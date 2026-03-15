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

BALANCE GUIDELINES:
- Hallway enemies (nodes n1, n2): moderate threat, HP 28-55 each, attacks 5-12, max 2 enemies
- Elite enemy (node n5): real challenge, HP 65-90, attacks 10-18, one unique mechanic
- Boss (node n6): HP 105-135, 4+ intents with escalating pattern, very dangerous
- Card costs: mostly 1-2 energy. Cards that cost 2 should be powerful.
- Keep damage numbers realistic: a 2-cost card dealing 20 damage is fine, but 50 is not.
- Cards should have exactly ONE behavior with trigger "onPlay" and 1-3 effects.
- Allowed effect types: damage, modifyStat, drawCards, gainEnergy, repeat, condition, heal, addCard, log
- Allowed stat names: block, strength, weak, vulnerable, hp, energy
- Relic triggers: onBattleStart, onCardPlayed, onTurnStart, onTurnEnd, onBattleEnd
- Relic effects should be moderate (e.g., +1 something per trigger, not +5).

THEMATIC GUIDANCE:
- Invent a unique dark sci-fi theme for this run (e.g., "corrupted cathedral", "deep ocean rig", "neural wasteland")
- All names, descriptions, enemy names, card names should fit the theme
- Be creative but consistent within the run

Return ONLY valid JSON matching this exact schema (no markdown, no explanation):

{
  "theme": "short thematic title for this run (3-6 words)",
  "encounters": {
    "hallway": [
      {
        "enemies": [
          {
            "name": "string",
            "maxHp": 28-55,
            "intents": [
              {"type": "attack|buff|attackBlock|debuff", "value": number_if_attack, "label": "string",
               "strength": number_optional, "block": number_optional,
               "weak": number_optional, "vulnerable": number_optional,
               "repeats": 1_or_2_optional}
            ]
          }
        ]
      }
    ],
    "elite": [
      {
        "enemies": [
          {
            "name": "string",
            "maxHp": 65-90,
            "intents": [/* 3-4 intents */]
          }
        ]
      }
    ],
    "boss": [
      {
        "enemies": [
          {
            "name": "string",
            "maxHp": 105-135,
            "intents": [/* 4-5 intents */]
          }
        ]
      }
    ]
  },
  "cards": [
    {
      "id": "unique_snake_case_id",
      "name": "Card Name",
      "cost": 1,
      "type": "Attack|Skill|Power",
      "rarity": "Common|Uncommon|Rare",
      "description": "Short effect description.",
      "behaviors": [
        {
          "trigger": "onPlay",
          "effects": [
            {"type": "damage", "target": "opponent", "amount": 9, "useCombatModifiers": true}
          ]
        }
      ]
    }
  ],
  "relics": [
    {
      "id": "unique_snake_case_id",
      "name": "Relic Name",
      "icon": "single emoji",
      "description": "Passive effect description.",
      "behaviors": [
        {
          "trigger": "onBattleStart|onCardPlayed|onTurnStart|onTurnEnd",
          "effects": [
            {"type": "modifyStat|gainEnergy|drawCards", ...}
          ]
        }
      ]
    }
  ],
  "levelArt": {
    "n1": {
      "title": "Floor 1",
      "weaponName": "string",
      "weaponDescription": "string (1 sentence)",
      "enemyName": "string (matches encounters.hallway[0].enemies[0].name)",
      "enemyDescription": "string (1 sentence)"
    },
    "n2": {"title": "Floor 2", "weaponName": "...", "weaponDescription": "...", "enemyName": "...", "enemyDescription": "..."},
    "n3": {"title": "Floor 3 — Campfire", "weaponName": "...", "weaponDescription": "...", "enemyName": "none", "enemyDescription": "A quiet rest point."},
    "n4": {"title": "Floor 4 — Vault", "weaponName": "...", "weaponDescription": "...", "enemyName": "none", "enemyDescription": "A hidden cache of relics."},
    "n5": {"title": "Floor 5 — Elite", "weaponName": "...", "weaponDescription": "...", "enemyName": "...", "enemyDescription": "..."},
    "n6": {"title": "Floor 6 — Boss", "weaponName": "...", "weaponDescription": "...", "enemyName": "...", "enemyDescription": "..."}
  },
  "mapNodes": [
    {"id": "n1", "type": "hallway", "label": "string"},
    {"id": "n2", "type": "hallway", "label": "string"},
    {"id": "n3", "type": "campfire", "label": "string"},
    {"id": "n4", "type": "treasure", "label": "string"},
    {"id": "n5", "type": "elite", "label": "string"},
    {"id": "n6", "type": "boss", "label": "string"}
  ],
  "imagePrompts": {
    "n1": {"weapon": "detailed image gen prompt for the weapon art", "enemy": "detailed image gen prompt for the enemy art"},
    "n2": {"weapon": "...", "enemy": "..."},
    "n5": {"weapon": "...", "enemy": "..."},
    "n6": {"weapon": "...", "enemy": "..."}
  }
}

Rules:
- Generate exactly 3 hallway encounter variants (different enemy combos)
- Generate exactly 1 elite encounter and 1 boss encounter
- Generate exactly 6 cards for the reward pool (mix of Attack/Skill, rarity Common/Uncommon/Rare)
- Generate exactly 3 relics
- Every intent must have a "label" string
- Attack intents must have "value" (integer)
- Buff/debuff intents must NOT have "value"; use strength/block/weak/vulnerable
- Image prompts: dark sci-fi fantasy art style, single subject on dark background, painterly, no text"""


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

    # Image prompts
    image_prompts = {}
    raw_prompts = data.get("imagePrompts") or {}
    for node_id in ("n1", "n2", "n5", "n6"):
        node_prompts = raw_prompts.get(node_id) or {}
        image_prompts[node_id] = {
            "weapon": str(node_prompts.get("weapon", ""))[:400],
            "enemy": str(node_prompts.get("enemy", ""))[:400],
        }

    return {
        "theme": str(data.get("theme", "Unknown Run"))[:60],
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
