"""
LLM-driven run generation via Google Gemini.

Generates a full run's content at game-start:
  - Enemy encounters for hallway/elite/boss nodes
  - Card reward pool (cards the player can acquire)
  - Relic pool (treasures available)
  - Map node descriptions and level art metadata

All generated content is validated against strict JSON schemas so the
game engine never has to trust raw LLM output blindly.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# ── Gemini REST endpoint ──────────────────────────────────────────────────────

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)


def _load_env() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    for env_file in (repo_root / ".env", repo_root / ".env.local"):
        if not env_file.exists():
            continue
        for line in env_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _get_api_key() -> Optional[str]:
    _load_env()
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def _call_gemini(prompt: str, retries: int = 3) -> str:
    import time

    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError(
            "Set GEMINI_API_KEY (or GOOGLE_API_KEY) in environment or .env/.env.local"
        )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json",
        },
    }

    last_exc: Exception = RuntimeError("No attempts made")
    for attempt in range(retries):
        try:
            resp = requests.post(
                GEMINI_URL,
                params={"key": api_key},
                json=payload,
                timeout=90,
            )
            if resp.status_code == 429:
                wait = 20 * (attempt + 1)
                logger.warning("Gemini rate limited (attempt %d/%d), retrying in %ds…", attempt + 1, retries, wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as exc:
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
    raise last_exc


# ── Prompt ────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """Ты — гейм-дизайнер тёмной sci-fi рогалик карточной игры (в стиле Slay the Spire).
Сгенерируй контент для ОДНОГО полного рана. Игрок начинает с 72 HP и базовой колодой
(4× Удар — 6 урона, 4× Защита — 5 блока, 1× Дробление — 8 урона + 2 уязвимости, 1× Концентрация — +2 силы).
Макс энергии за ход: 3.

⚠️ ЯЗЫК: Все названия (карты, враги, реликвии, ноды, описания, label у интентов) — ТОЛЬКО НА РУССКОМ.
ID карт и реликвий — snake_case латиницей (для технических нужд).

═══════════════════════════════════════
БАЛАНС
═══════════════════════════════════════
- Коридорные враги (n1, n2, n4, n5, n9): умеренная угроза, HP 28-58, атаки 5-13, макс 2 врага в группе
- Элита (n7, n10): серьёзный вызов, HP 65-100, атаки 10-20, уникальная механика (яд/лечение/усиление)
- Босс (n12): HP 115-150, 4+ интентов, нарастающая опасность, должен быть ЭПИЧНЫМ
- Стоимость карт: 0-2 энергии. 2 = мощная карта. 0 = очень слабая (кантрип).
- Урон: атака за 2 энергии на 20 — нормально; 40+ — слишком много.
- Блок: 8-14 типично для карты Навыка за 1 энергию.
- У карт ровно ОДИН behavior с trigger "onPlay".
- Реликвии: умеренный эффект за триггер.
- Интент "poison" — накладывает яд на игрока (amount: 2-5).
- Интент "heal" — враг восстанавливает себе HP (amount: 10-25).

═══════════════════════════════════════
EFFECT REFERENCE (all available types)
═══════════════════════════════════════

Basic effects:
  {"type":"damage","target":"opponent","amount":9,"useCombatModifiers":true}
  {"type":"gainBlock","target":"self","amount":8}
  {"type":"modifyStat","target":"self","stat":"strength","amount":2}
    stat options: block, strength, weak, vulnerable, hp, energy
  {"type":"heal","target":"self","amount":6}
  {"type":"drawCards","amount":2}
  {"type":"gainEnergy","amount":1}
  {"type":"addCard","cardId":"strike","zone":"hand"}
    zone options: hand, drawPile, discardPile
  {"type":"log","text":"Something happens."}

Dynamic amounts (use as "amount" value instead of a number):
  "cardsInHand"      — number of cards currently in hand
  "playerStrength"   — player's current strength stat
  "playerMissingHp"  — maxHp minus current hp
  "playerHpPercent"  — current hp as percentage of maxHp
  "enemyCount"       — number of alive enemies
  "deckSize"         — total cards in deck
  "discardSize"      — cards in discard pile
  "targetMissingHp"  — selected enemy's missing HP

Composite / advanced effects:
  {"type":"repeat","times":3,"effects":[...]}
    — execute inner effects N times (times can be a dynamic amount)

  {"type":"condition",
   "condition":{"target":"self","stat":"hp","operator":"lt","valuePercent":50},
   "effects":[...],
   "elseEffects":[...]}
    — conditional branch. operators: gt, gte, lt, lte, eq
    — use "valuePercent" (0-100) instead of "value" to compare as % of maxHp

  {"type":"multiHit","target":"opponent","hits":3,"amount":4,"escalate":1.5,"useCombatModifiers":true}
    — hit N times; each subsequent hit multiplied by escalate (omit escalate for equal hits)

  {"type":"splitDamage","amount":18,"useCombatModifiers":true}
    — divide total damage evenly across ALL alive enemies

  {"type":"lifesteal","target":"opponent","amount":10,"steal":0.5,"useCombatModifiers":true}
    — deal damage, heal self for steal fraction of damage dealt (steal: 0.0-1.0)

  {"type":"execute","target":"opponent","thresholdPercent":20}
    — instantly kill target if hp <= thresholdPercent% of maxHp
    — OR use "threshold": 15 for a flat HP value

  {"type":"echo"}
    — re-apply the onPlay effects of the PREVIOUS card played this turn

  {"type":"exhaustRandom","amount":1}
    — exhaust N random cards from hand (removes them permanently this combat)

EXAMPLE CARDS using advanced mechanics:

  // Hits 3 times, each hit 50% stronger
  {"id":"chain_strike","name":"Chain Strike","cost":2,"type":"Attack","rarity":"Uncommon",
   "description":"Deal 5 damage 3 times, each hit 50% stronger.",
   "behaviors":[{"trigger":"onPlay","effects":[
     {"type":"multiHit","target":"opponent","hits":3,"amount":5,"escalate":1.5,"useCombatModifiers":true}
   ]}]}

  // More damage when low HP
  {"id":"death_rattle","name":"Death Rattle","cost":1,"type":"Attack","rarity":"Rare",
   "description":"Deal damage equal to your missing HP.",
   "behaviors":[{"trigger":"onPlay","effects":[
     {"type":"damage","target":"opponent","amount":"playerMissingHp","useCombatModifiers":true}
   ]}]}

  // Split damage + draw
  {"id":"shrapnel","name":"Shrapnel","cost":1,"type":"Attack","rarity":"Common",
   "description":"Deal 12 damage split among all enemies. Draw 1.",
   "behaviors":[{"trigger":"onPlay","effects":[
     {"type":"splitDamage","amount":12,"useCombatModifiers":true},
     {"type":"drawCards","amount":1}
   ]}]}

  // Execute below 25%
  {"id":"mercy_kill","name":"Mercy Kill","cost":0,"type":"Skill","rarity":"Uncommon",
   "description":"If enemy is below 25% HP, kill it instantly.",
   "behaviors":[{"trigger":"onPlay","effects":[
     {"type":"execute","target":"opponent","thresholdPercent":25}
   ]}]}

  // Block based on hand size
  {"id":"iron_veil","name":"Iron Veil","cost":1,"type":"Skill","rarity":"Common",
   "description":"Gain block equal to the number of cards in your hand.",
   "behaviors":[{"trigger":"onPlay","effects":[
     {"type":"gainBlock","target":"self","amount":"cardsInHand"}
   ]}]}

  // Lifesteal
  {"id":"parasite_blade","name":"Parasite Blade","cost":2,"type":"Attack","rarity":"Rare",
   "description":"Deal 14 damage. Heal for half the damage dealt.",
   "behaviors":[{"trigger":"onPlay","effects":[
     {"type":"lifesteal","target":"opponent","amount":14,"steal":0.5,"useCombatModifiers":true}
   ]}]}

  // Conditional: bonus if HP < 50%
  {"id":"berserker_cut","name":"Berserker Cut","cost":1,"type":"Attack","rarity":"Uncommon",
   "description":"Deal 8 damage. If below half HP, deal 8 more.",
   "behaviors":[{"trigger":"onPlay","effects":[
     {"type":"damage","target":"opponent","amount":8,"useCombatModifiers":true},
     {"type":"condition",
      "condition":{"target":"self","stat":"hp","operator":"lt","valuePercent":50},
      "effects":[{"type":"damage","target":"opponent","amount":8,"useCombatModifiers":true}]}
   ]}]}

═══════════════════════════════════════
ТЕМАТИКА
═══════════════════════════════════════
- Придумай ОДНУ уникальную тёмную sci-fi тему для рана (например: "Мутация реакторного ядра", "Кладбище призрачных кораблей", "Улей нейропаразитов")
- Выведи "worldStyle": строку визуального стиля 15-25 слов, которую используют ВСЕ промпты изображений
  Пример: "dark industrial gothic, corroded iron and toxic green glow, painterly oil texture, dramatic underlighting, high contrast"
- Каждое название, описание, имя врага, метка ноды — тематически связаны и на русском
- Каждая карта должна иметь уникальную механическую изюминку — не генерируй 8 одинаковых "нанести X урона"

═══════════════════════════════════════
ТИПЫ ИНТЕНТОВ ВРАГОВ
═══════════════════════════════════════
  attack      — {"type":"attack","value":10,"label":"Удар 10"}
  attackBlock — {"type":"attackBlock","value":8,"block":6,"label":"Удар + Блок"}
  buff        — {"type":"buff","strength":3,"label":"Усиление +3 Силы"}  (или block)
  debuff      — {"type":"debuff","weak":2,"label":"Ослабление 2"}  (или vulnerable)
  poison      — {"type":"poison","amount":4,"label":"Яд +4"}  — накладывает яд на игрока
  heal        — {"type":"heal","amount":15,"label":"Регенерация 15"}  — враг лечит себя

═══════════════════════════════════════
СХЕМА ВЫВОДА (ТОЛЬКО этот JSON, ничего лишнего)
═══════════════════════════════════════

{
  "theme": "короткое название темы (3-6 слов, по-русски)",
  "worldStyle": "общий визуальный стиль для ВСЕХ изображений (15-25 слов на английском, НЕ photorealistic, НЕ 3D — только painterly/oil painting/hand-drawn)",
  "encounters": {
    "hallway": [
      {"enemies": [{"name":"строка по-русски","description":"1 предложение-флавор по-русски","maxHp":28-58,"intents":[
        {"type":"attack|buff|attackBlock|debuff|poison","value":число_если_атака,"label":"по-русски",
         "strength":опционально,"block":опционально,"weak":опционально,"vulnerable":опционально,"amount":опционально,"repeats":опционально}
      ]}]},
      {"enemies": [/* вариант 2, можно 2 врага */]},
      {"enemies": [/* вариант 3 */]},
      {"enemies": [/* вариант 4 */]},
      {"enemies": [/* вариант 5 */]}
    ],
    "elite": [
      {"enemies": [{"name":"по-русски","description":"1 предложение по-русски","maxHp":65-100,"intents":[/* 3-4 интента, обязательно яд ИЛИ лечение ИЛИ усиление */]}]},
      {"enemies": [/* вариант 2 */]}
    ],
    "boss": [{"enemies": [{"name":"по-русски","description":"лор босса по-русски","maxHp":115-150,"intents":[/* 4-5 интентов, комбо яд+лечение+атака */]}]}]
  },
  "cards": [
    {
      "id": "snake_case_latin_id",
      "name": "Название на русском",
      "cost": 0-2,
      "type": "Attack|Skill|Power",
      "rarity": "Common|Uncommon|Rare",
      "description": "Короткое описание эффекта на русском (1-2 предложения).",
      "behaviors": [{"trigger":"onPlay","effects":[/* 1-4 эффекта из справочника выше */]}]
    }
  ],
  "relics": [
    {
      "id": "snake_case_latin_id",
      "name": "Название реликвии на русском",
      "icon": "одно эмодзи",
      "description": "Описание пассивного эффекта на русском.",
      "behaviors": [{"trigger":"onBattleStart|onCardPlayed|onTurnStart|onTurnEnd|onBattleEnd",
                     "effects":[/* 1-2 эффекта */]}]
    }
  ],
  "levelArt": {
    "n1":  {"title":"Этаж 1","weaponName":"по-русски","weaponDescription":"1 предложение по-русски","enemyName":"совпадает с hallway[0].enemies[0].name","enemyDescription":"1 предложение по-русски"},
    "n2":  {"title":"Этаж 2","weaponName":"по-русски","weaponDescription":"1 предложение","enemyName":"hallway[1] первый враг","enemyDescription":"1 предложение"},
    "n3":  {"title":"Этаж 3 — Привал","weaponName":"по-русски","weaponDescription":"1 предложение","enemyName":"нет","enemyDescription":"Момент тишины."},
    "n4":  {"title":"Этаж 4","weaponName":"по-русски","weaponDescription":"1 предложение","enemyName":"hallway[2] первый враг","enemyDescription":"1 предложение"},
    "n5":  {"title":"Этаж 5","weaponName":"по-русски","weaponDescription":"1 предложение","enemyName":"hallway[3] первый враг","enemyDescription":"1 предложение"},
    "n6":  {"title":"Этаж 6 — Тайник","weaponName":"по-русски","weaponDescription":"1 предложение","enemyName":"нет","enemyDescription":"Скрытый запас реликвий."},
    "n7":  {"title":"Этаж 7 — Элита","weaponName":"по-русски","weaponDescription":"1 предложение","enemyName":"elite[0] имя врага","enemyDescription":"1 предложение"},
    "n8":  {"title":"Этаж 8 — Привал","weaponName":"по-русски","weaponDescription":"1 предложение","enemyName":"нет","enemyDescription":"Последний отдых перед вершиной."},
    "n9":  {"title":"Этаж 9","weaponName":"по-русски","weaponDescription":"1 предложение","enemyName":"hallway[4] первый враг","enemyDescription":"1 предложение"},
    "n10": {"title":"Этаж 10 — Элита","weaponName":"по-русски","weaponDescription":"1 предложение","enemyName":"elite[1] имя врага","enemyDescription":"1 предложение"},
    "n11": {"title":"Этаж 11 — Привал","weaponName":"по-русски","weaponDescription":"1 предложение","enemyName":"нет","enemyDescription":"Финальный привал."},
    "n12": {"title":"Этаж 12 — Босс","weaponName":"по-русски","weaponDescription":"1 предложение","enemyName":"имя босса","enemyDescription":"1 предложение по-русски"}
  },
  "mapNodes": [
    {"id":"n1", "type":"hallway",  "label":"по-русски"},
    {"id":"n2", "type":"hallway",  "label":"по-русски"},
    {"id":"n3", "type":"campfire", "label":"по-русски"},
    {"id":"n4", "type":"hallway",  "label":"по-русски"},
    {"id":"n5", "type":"hallway",  "label":"по-русски"},
    {"id":"n6", "type":"treasure", "label":"по-русски"},
    {"id":"n7", "type":"elite",    "label":"по-русски"},
    {"id":"n8", "type":"campfire", "label":"по-русски"},
    {"id":"n9", "type":"hallway",  "label":"по-русски"},
    {"id":"n10","type":"elite",    "label":"по-русски"},
    {"id":"n11","type":"campfire", "label":"по-русски"},
    {"id":"n12","type":"boss",     "label":"по-русски"}
  ],
  "imagePrompts": {
    "n1":  {"weapon":"промпт НАЧИНАЕТСЯ с worldStyle, затем описание оружия — painterly, hand-drawn","enemy":"промпт НАЧИНАЕТСЯ с worldStyle, затем описание врага — oil painting, dramatic lighting"},
    "n2":  {"weapon":"...","enemy":"..."},
    "n4":  {"weapon":"...","enemy":"..."},
    "n5":  {"weapon":"...","enemy":"..."},
    "n7":  {"weapon":"...","enemy":"..."},
    "n9":  {"weapon":"...","enemy":"..."},
    "n10": {"weapon":"...","enemy":"..."},
    "n12": {"weapon":"...","enemy":"..."}
  }
}

СТРОГИЕ ПРАВИЛА:
- Ровно 5 вариантов hallway, 2 варианта elite, 1 boss
- Ровно 10 карт — минимум 4 используют продвинутые эффекты (multiHit/splitDamage/lifesteal/execute/echo/condition/динамические amount)
- Ровно 4 реликвии
- У каждого интента есть "label" на русском
- Атакующие интенты имеют "value"; buff/debuff используют strength/block/weak/vulnerable; poison/heal используют "amount"
- Промпты изображений: каждый начинается с worldStyle дословно, затем специфика субъекта
- worldStyle ОБЯЗАТЕЛЬНО содержит "painterly" или "oil painting" или "hand-drawn" — никогда "photorealistic" или "3D"
- Никакого markdown, никаких пояснений — только чистый JSON"""


# ── Validation ────────────────────────────────────────────────────────────────

def _extract_json(raw: str) -> Dict[str, Any]:
    """Strip markdown fences if present, then parse JSON."""
    stripped = raw.strip()
    # Remove ```json ... ``` wrappers
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", stripped)
    if match:
        stripped = match.group(1)
    return json.loads(stripped)


def _validate_intent(intent: Dict[str, Any]) -> Dict[str, Any]:
    intent_type = intent.get("type", "attack")
    label = str(intent.get("label", f"{intent_type}"))
    base = {"type": intent_type, "label": label}

    if intent_type in ("attack", "attackBlock"):
        base["value"] = max(1, int(intent.get("value", 6)))
        if intent_type == "attackBlock":
            base["block"] = max(0, int(intent.get("block", 4)))
        if intent.get("repeats", 1) > 1:
            base["repeats"] = min(3, int(intent["repeats"]))
    elif intent_type == "buff":
        if "strength" in intent:
            base["strength"] = max(1, int(intent["strength"]))
        if "block" in intent:
            base["block"] = max(0, int(intent["block"]))
    elif intent_type == "debuff":
        if "weak" in intent:
            base["weak"] = max(1, int(intent["weak"]))
        if "vulnerable" in intent:
            base["vulnerable"] = max(1, int(intent["vulnerable"]))
    elif intent_type == "poison":
        base["amount"] = max(1, min(10, int(intent.get("amount", 3))))
    elif intent_type == "heal":
        base["amount"] = max(1, min(40, int(intent.get("amount", 12))))

    return base


def _validate_enemy(enemy: Dict[str, Any], hp_range: tuple[int, int]) -> Dict[str, Any]:
    lo, hi = hp_range
    max_hp = max(lo, min(hi, int(enemy.get("maxHp", lo))))
    intents = [_validate_intent(i) for i in (enemy.get("intents") or [])]
    if not intents:
        intents = [{"type": "attack", "value": 6, "label": "Strike 6"}]
    return {
        "name": str(enemy.get("name", "Unknown"))[:40],
        "description": str(enemy.get("description", ""))[:160],
        "maxHp": max_hp,
        "intents": intents,
    }


def _validate_card(card: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": re.sub(r"[^a-z0-9_]", "_", str(card.get("id", "card")).lower())[:30],
        "name": str(card.get("name", "Card"))[:40],
        "cost": max(0, min(3, int(card.get("cost", 1)))),
        "type": card.get("type", "Attack") if card.get("type") in ("Attack", "Skill", "Power") else "Attack",
        "rarity": card.get("rarity", "Common") if card.get("rarity") in ("Common", "Uncommon", "Rare", "Starter") else "Common",
        "description": str(card.get("description", ""))[:120],
        "behaviors": card.get("behaviors") or [],
    }


def _validate_relic(relic: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": re.sub(r"[^a-z0-9_]", "_", str(relic.get("id", "relic")).lower())[:30],
        "name": str(relic.get("name", "Relic"))[:40],
        "icon": str(relic.get("icon", "✦"))[:4],
        "description": str(relic.get("description", ""))[:120],
        "behaviors": relic.get("behaviors") or [],
    }


def _validate_run(data: Dict[str, Any]) -> Dict[str, Any]:
    enc = data.get("encounters", {})

    # Encounters
    hallway_raw = enc.get("hallway") or []
    hallway = []
    for h in hallway_raw[:5]:
        enemies = [_validate_enemy(e, (28, 55)) for e in (h.get("enemies") or [])]
        if enemies:
            hallway.append({"enemies": enemies})
    if not hallway:
        hallway = [{"enemies": [{"name": "Grunt", "description": "", "maxHp": 38, "intents": [{"type": "attack", "value": 7, "label": "Strike 7"}]}]}]

    elite_raw_list = enc.get("elite") or [{}]
    elite = []
    for er in elite_raw_list[:2]:
        elite_enemies = [_validate_enemy(e, (65, 95)) for e in (er.get("enemies") or [])]
        if elite_enemies:
            elite.append({"enemies": elite_enemies})
    if not elite:
        elite = [{"enemies": [{"name": "Guardian", "description": "", "maxHp": 72, "intents": [{"type": "attack", "value": 12, "label": "Crush 12"}]}]}]

    boss_raw = (enc.get("boss") or [{}])[0]
    boss_enemies = [_validate_enemy(e, (110, 145)) for e in (boss_raw.get("enemies") or [])]
    if not boss_enemies:
        boss_enemies = [{"name": "Overlord", "description": "", "maxHp": 125, "intents": [{"type": "attack", "value": 16, "label": "Pulse 16"}]}]

    encounters = {
        "hallway": hallway,
        "elite": elite,
        "boss": [{"enemies": boss_enemies}],
    }

    # Cards
    cards_raw = data.get("cards") or []
    cards = [_validate_card(c) for c in cards_raw[:10]]

    # Relics
    relics_raw = data.get("relics") or []
    relics = [_validate_relic(r) for r in relics_raw[:4]]

    # Level art — 12 nodes
    level_art_raw = data.get("levelArt") or {}
    level_art: Dict[str, Any] = {}
    for node_id in ("n1", "n2", "n3", "n4", "n5", "n6", "n7", "n8", "n9", "n10", "n11", "n12"):
        raw = level_art_raw.get(node_id) or {}
        level_art[node_id] = {
            "title": str(raw.get("title", f"Floor {node_id[1:]}")),
            "weaponName": str(raw.get("weaponName", "Unknown Weapon")),
            "weaponDescription": str(raw.get("weaponDescription", ""))[:160],
            "weaponImage": f"./src/assets/generated/run/{node_id}-weapon.png",
            "enemyName": str(raw.get("enemyName", "Unknown")),
            "enemyDescription": str(raw.get("enemyDescription", ""))[:160],
            "enemyImage": f"./src/assets/generated/run/{node_id}-enemy.png",
        }

    # Map nodes — 12 nodes
    map_nodes_raw = data.get("mapNodes") or []
    node_types = {
        "n1": "hallway", "n2": "hallway", "n3": "campfire",
        "n4": "hallway", "n5": "hallway", "n6": "treasure",
        "n7": "elite",   "n8": "campfire", "n9": "hallway",
        "n10": "elite",  "n11": "campfire", "n12": "boss",
    }
    map_nodes = []
    node_map = {n["id"]: n for n in map_nodes_raw if isinstance(n, dict)}
    for i, (nid, ntype) in enumerate(node_types.items()):
        raw_node = node_map.get(nid, {})
        map_nodes.append({
            "id": nid,
            "type": ntype,
            "label": str(raw_node.get("label", nid)),
            "index": i,
            "completed": False,
            "available": i == 0,
        })

    # worldStyle: shared visual direction string for all image prompts
    world_style = str(data.get("worldStyle", ""))[:200].strip()

    # Image prompts — prepend worldStyle if not already present
    image_prompts = {}
    raw_prompts = data.get("imagePrompts") or {}
    for node_id in ("n1", "n2", "n4", "n5", "n7", "n9", "n10", "n12"):
        node_prompts = raw_prompts.get(node_id) or {}
        weapon_prompt = str(node_prompts.get("weapon", ""))[:500]
        enemy_prompt = str(node_prompts.get("enemy", ""))[:500]
        if world_style and not weapon_prompt.startswith(world_style[:30]):
            weapon_prompt = f"{world_style}, {weapon_prompt}" if weapon_prompt else world_style
        if world_style and not enemy_prompt.startswith(world_style[:30]):
            enemy_prompt = f"{world_style}, {enemy_prompt}" if enemy_prompt else world_style
        image_prompts[node_id] = {
            "weapon": weapon_prompt[:600],
            "enemy": enemy_prompt[:600],
        }

    return {
        "theme": str(data.get("theme", "Unknown Run"))[:60],
        "worldStyle": world_style,
        "encounters": encounters,
        "cards": cards,
        "relics": relics,
        "levelArt": level_art,
        "mapNodes": map_nodes,
        "imagePrompts": image_prompts,
    }


# ── Public API ────────────────────────────────────────────────────────────────

def generate_run() -> Dict[str, Any]:
    """
    Call Gemini to generate a full run configuration.
    Returns validated dict ready for consumption by game.py.
    Raises on network / API errors — caller should fall back to static content.
    """
    raw_text = _call_gemini(_SYSTEM_PROMPT)
    raw_data = _extract_json(raw_text)
    return _validate_run(raw_data)
