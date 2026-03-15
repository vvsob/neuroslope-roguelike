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


def _call_gemini(prompt: str) -> str:
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError(
            "Set GEMINI_API_KEY (or GOOGLE_API_KEY) in environment or .env/.env.local"
        )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json",
        },
    }

    resp = requests.post(
        GEMINI_URL,
        params={"key": api_key},
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


# ── Prompt ────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a game designer for a dark sci-fi roguelike card game (similar to Slay the Spire).
Generate content for ONE full game run. The player starts with 72 HP and a basic deck
(4× Strike deal 6 damage, 4× Defend give 5 block, 1× Bash deal 10+2vulnerable, 1× Focus draw+1 each turn).
Max player energy per turn: 3.

═══════════════════════════════════════
BALANCE GUIDELINES
═══════════════════════════════════════
- Hallway enemies (n1, n2): moderate threat, HP 28-55, attacks 5-12, max 2 enemies per encounter
- Elite (n5): real challenge, HP 65-90, attacks 10-18, must have one unique mechanic
- Boss (n6): HP 105-135, 4+ intents, escalating danger pattern
- Card costs: 0-2 energy. Cost 2 = powerful. Cost 0 = very weak (cantrip).
- Damage numbers: a 2-cost Attack dealing 20 is fine; 40+ is too strong.
- Block numbers: 8-14 is typical for a 1-cost Skill.
- Cards must have exactly ONE behavior with trigger "onPlay".
- Relic effects: moderate per-trigger. No "+5 strength on every card played".

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
THEMATIC GUIDANCE
═══════════════════════════════════════
- Invent ONE unique dark sci-fi theme for this run (e.g. "frozen reactor meltdown", "ghost ship graveyard", "neural parasite hive")
- Derive a "worldStyle": a 15-25 word visual art direction string that ALL image prompts must share
  Example: "dark industrial gothic, corroded iron and toxic green glow, painterly oil texture, dramatic underlighting, high contrast"
- Every name, description, card name, enemy name, node label must feel thematically consistent
- Each card should have a unique mechanical hook — avoid generating 6 plain "deal X damage" cards

═══════════════════════════════════════
OUTPUT SCHEMA (return ONLY this JSON)
═══════════════════════════════════════

{
  "theme": "short thematic title (3-6 words)",
  "worldStyle": "shared visual style for ALL art in this run (15-25 words)",
  "encounters": {
    "hallway": [
      {"enemies": [{"name":"string","maxHp":28-55,"intents":[
        {"type":"attack|buff|attackBlock|debuff","value":number_if_attack,"label":"string",
         "strength":optional,"block":optional,"weak":optional,"vulnerable":optional,"repeats":optional}
      ]}]},
      {"enemies": [/* variant 2 */]},
      {"enemies": [/* variant 3, can be 2 enemies */]}
    ],
    "elite": [{"enemies": [{"name":"string","maxHp":65-90,"intents":[/* 3-4 intents */]}]}],
    "boss":  [{"enemies": [{"name":"string","maxHp":105-135,"intents":[/* 4-5 intents */]}]}]
  },
  "cards": [
    {
      "id": "unique_snake_case_id",
      "name": "Card Name",
      "cost": 0-2,
      "type": "Attack|Skill|Power",
      "rarity": "Common|Uncommon|Rare",
      "description": "Short effect description (1-2 sentences).",
      "behaviors": [{"trigger":"onPlay","effects":[/* 1-4 effects from the reference above */]}]
    }
  ],
  "relics": [
    {
      "id": "unique_snake_case_id",
      "name": "Relic Name",
      "icon": "single emoji",
      "description": "Passive effect description.",
      "behaviors": [{"trigger":"onBattleStart|onCardPlayed|onTurnStart|onTurnEnd|onBattleEnd",
                     "effects":[/* 1-2 effects */]}]
    }
  ],
  "levelArt": {
    "n1": {"title":"Floor 1","weaponName":"string","weaponDescription":"1 sentence","enemyName":"matches hallway[0].enemies[0].name","enemyDescription":"1 sentence"},
    "n2": {"title":"Floor 2","weaponName":"string","weaponDescription":"1 sentence","enemyName":"matches hallway[1] or hallway[2] first enemy","enemyDescription":"1 sentence"},
    "n3": {"title":"Floor 3 — Campfire","weaponName":"string","weaponDescription":"1 sentence","enemyName":"none","enemyDescription":"A quiet rest point."},
    "n4": {"title":"Floor 4 — Vault","weaponName":"string","weaponDescription":"1 sentence","enemyName":"none","enemyDescription":"A hidden cache of relics."},
    "n5": {"title":"Floor 5 — Elite","weaponName":"string","weaponDescription":"1 sentence","enemyName":"matches elite enemy name","enemyDescription":"1 sentence"},
    "n6": {"title":"Floor 6 — Boss","weaponName":"string","weaponDescription":"1 sentence","enemyName":"matches boss enemy name","enemyDescription":"1 sentence"}
  },
  "mapNodes": [
    {"id":"n1","type":"hallway","label":"string"},
    {"id":"n2","type":"hallway","label":"string"},
    {"id":"n3","type":"campfire","label":"string"},
    {"id":"n4","type":"treasure","label":"string"},
    {"id":"n5","type":"elite","label":"string"},
    {"id":"n6","type":"boss","label":"string"}
  ],
  "imagePrompts": {
    "n1": {
      "weapon": "image prompt that BEGINS with worldStyle, then describes the weapon specifically",
      "enemy": "image prompt that BEGINS with worldStyle, then describes the enemy specifically"
    },
    "n2": {"weapon":"...","enemy":"..."},
    "n5": {"weapon":"...","enemy":"..."},
    "n6": {"weapon":"...","enemy":"..."}
  }
}

STRICT RULES:
- Exactly 3 hallway variants, 1 elite, 1 boss
- Exactly 6 cards — at least 2 must use advanced effects (multiHit/splitDamage/lifesteal/execute/echo/condition/dynamic amounts)
- Exactly 3 relics
- Every intent needs a "label"
- Attack intents need "value"; buff/debuff use strength/block/weak/vulnerable instead
- Image prompts: each one starts with worldStyle verbatim, then adds subject-specific details
- No markdown, no explanation — pure JSON only"""


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

    return base


def _validate_enemy(enemy: Dict[str, Any], hp_range: tuple[int, int]) -> Dict[str, Any]:
    lo, hi = hp_range
    max_hp = max(lo, min(hi, int(enemy.get("maxHp", lo))))
    intents = [_validate_intent(i) for i in (enemy.get("intents") or [])]
    if not intents:
        intents = [{"type": "attack", "value": 6, "label": "Strike 6"}]
    return {
        "name": str(enemy.get("name", "Unknown"))[:40],
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
    for h in hallway_raw[:3]:
        enemies = [_validate_enemy(e, (28, 55)) for e in (h.get("enemies") or [])]
        if enemies:
            hallway.append({"enemies": enemies})
    if not hallway:
        hallway = [{"enemies": [{"name": "Grunt", "maxHp": 38, "intents": [{"type": "attack", "value": 7, "label": "Strike 7"}]}]}]

    elite_raw = (enc.get("elite") or [{}])[0]
    elite_enemies = [_validate_enemy(e, (65, 90)) for e in (elite_raw.get("enemies") or [])]
    if not elite_enemies:
        elite_enemies = [{"name": "Guardian", "maxHp": 72, "intents": [{"type": "attack", "value": 12, "label": "Crush 12"}]}]

    boss_raw = (enc.get("boss") or [{}])[0]
    boss_enemies = [_validate_enemy(e, (105, 135)) for e in (boss_raw.get("enemies") or [])]
    if not boss_enemies:
        boss_enemies = [{"name": "Overlord", "maxHp": 120, "intents": [{"type": "attack", "value": 16, "label": "Pulse 16"}]}]

    encounters = {
        "hallway": hallway,
        "elite": [{"enemies": elite_enemies}],
        "boss": [{"enemies": boss_enemies}],
    }

    # Cards
    cards_raw = data.get("cards") or []
    cards = [_validate_card(c) for c in cards_raw[:6]]

    # Relics
    relics_raw = data.get("relics") or []
    relics = [_validate_relic(r) for r in relics_raw[:3]]

    # Level art
    level_art_raw = data.get("levelArt") or {}
    level_art: Dict[str, Any] = {}
    for node_id in ("n1", "n2", "n3", "n4", "n5", "n6"):
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

    # Map nodes
    map_nodes_raw = data.get("mapNodes") or []
    node_types = {"n1": "hallway", "n2": "hallway", "n3": "campfire", "n4": "treasure", "n5": "elite", "n6": "boss"}
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
    for node_id in ("n1", "n2", "n5", "n6"):
        node_prompts = raw_prompts.get(node_id) or {}
        weapon_prompt = str(node_prompts.get("weapon", ""))[:500]
        enemy_prompt = str(node_prompts.get("enemy", ""))[:500]
        # Ensure worldStyle is prepended if present and not already included
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
