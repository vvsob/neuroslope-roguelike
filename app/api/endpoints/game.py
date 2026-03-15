import asyncio
import copy
import logging
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from app.api.dependencies import get_current_user
from app.crud.game import GameCRUD
from app.db.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/game", tags=["Game"])

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_IMAGE_DIR = REPO_ROOT / "src" / "assets" / "generated" / "run"

# ── Data libraries (ported from frontend) ─────────────────────────────────────

STARTING_DECK = [
    "strike",
    "strike",
    "strike",
    "strike",
    "defend",
    "defend",
    "defend",
    "defend",
    "bash",
    "focus",
]

CARD_LIBRARY: Dict[str, Dict[str, Any]] = {
    "strike": {
        "id": "strike",
        "name": "Strike",
        "cost": 1,
        "type": "Attack",
        "rarity": "Starter",
        "description": "Deal 6 damage.",
        "behaviors": [
            {
                "trigger": "onPlay",
                "effects": [
                    {"type": "damage", "target": "opponent", "amount": 6, "useCombatModifiers": True},
                    {"type": "log", "text": "{playerName} slashes for 6."},
                ],
            }
        ],
    },
    "defend": {
        "id": "defend",
        "name": "Defend",
        "cost": 1,
        "type": "Skill",
        "rarity": "Starter",
        "description": "Gain 5 block.",
        "behaviors": [
            {
                "trigger": "onPlay",
                "effects": [
                    {"type": "modifyStat", "target": "self", "stat": "block", "amount": 5},
                    {"type": "log", "text": "{playerName} braces for 5 block."},
                ],
            }
        ],
    },
    "bash": {
        "id": "bash",
        "name": "Bash",
        "cost": 2,
        "type": "Attack",
        "rarity": "Starter",
        "description": "Deal 8 damage. Apply 2 Vulnerable.",
        "behaviors": [
            {
                "trigger": "onPlay",
                "effects": [
                    {"type": "damage", "target": "opponent", "amount": 8, "useCombatModifiers": True},
                    {"type": "modifyStat", "target": "opponent", "stat": "vulnerable", "amount": 2},
                    {"type": "log", "text": "{playerName} bashes for 8 and applies Vulnerable."},
                ],
            }
        ],
    },
    "focus": {
        "id": "focus",
        "name": "Focus",
        "cost": 1,
        "type": "Skill",
        "rarity": "Starter",
        "description": "Gain 2 Strength this combat.",
        "behaviors": [
            {
                "trigger": "onPlay",
                "effects": [
                    {"type": "modifyStat", "target": "self", "stat": "strength", "amount": 2},
                    {"type": "log", "text": "{playerName}'s stance sharpens. Gain 2 Strength."},
                ],
            }
        ],
    },
    "quick_slash": {
        "id": "quick_slash",
        "name": "Quick Slash",
        "cost": 1,
        "type": "Attack",
        "rarity": "Common",
        "description": "Deal 7 damage. Draw 1 card.",
        "behaviors": [
            {
                "trigger": "onPlay",
                "effects": [
                    {"type": "damage", "target": "opponent", "amount": 7, "useCombatModifiers": True},
                    {"type": "drawCards", "amount": 1},
                    {"type": "log", "text": "{playerName} lands Quick Slash and draws 1 card."},
                ],
            }
        ],
    },
    "iron_shell": {
        "id": "iron_shell",
        "name": "Iron Shell",
        "cost": 1,
        "type": "Skill",
        "rarity": "Common",
        "description": "Gain 7 block. Gain 1 Metallicize.",
        "behaviors": [
            {
                "trigger": "onPlay",
                "effects": [
                    {"type": "modifyStat", "target": "self", "stat": "block", "amount": 7},
                    {"type": "modifyStat", "target": "self", "stat": "metallicize", "amount": 1},
                    {"type": "log", "text": "{playerName} fortifies with Iron Shell."},
                ],
            }
        ],
    },
    "cleave": {
        "id": "cleave",
        "name": "Cleave",
        "cost": 1,
        "type": "Attack",
        "rarity": "Common",
        "description": "Deal 9 damage to all enemies.",
        "behaviors": [
            {
                "trigger": "onPlay",
                "effects": [
                    {"type": "damage", "target": "allEnemies", "amount": 9, "useCombatModifiers": True},
                    {"type": "log", "text": "{playerName} tears through the enemy line for 9."},
                ],
            }
        ],
    },
    "second_wind": {
        "id": "second_wind",
        "name": "Second Wind",
        "cost": 1,
        "type": "Skill",
        "rarity": "Common",
        "description": "Heal 4 HP. Exhaust.",
        "keywords": ["exhaust"],
        "behaviors": [
            {
                "trigger": "onPlay",
                "effects": [
                    {"type": "heal", "target": "self", "amount": 4},
                    {"type": "log", "text": "{playerName} recovers 4 HP."},
                ],
            }
        ],
    },
    "ember_script": {
        "id": "ember_script",
        "name": "Ember Script",
        "cost": 1,
        "type": "Skill",
        "rarity": "Uncommon",
        "description": "When drawn, gain 1 Energy. Exhaust.",
        "keywords": ["exhaust"],
        "behaviors": [
            {
                "trigger": "onDraw",
                "effects": [
                    {"type": "gainEnergy", "amount": 1},
                    {"type": "log", "text": "Ember Script surges as it enters your hand. Gain 1 Energy."},
                ],
            }
        ],
    },
    "mirrored_edge": {
        "id": "mirrored_edge",
        "name": "Mirrored Edge",
        "cost": 1,
        "type": "Attack",
        "rarity": "Uncommon",
        "description": "Deal 5 damage twice.",
        "behaviors": [
            {
                "trigger": "onPlay",
                "effects": [
                    {
                        "type": "repeat",
                        "times": 2,
                        "effects": [
                            {"type": "damage", "target": "opponent", "amount": 5, "useCombatModifiers": True}
                        ],
                    },
                    {"type": "log", "text": "{playerName} cuts twice with Mirrored Edge."},
                ],
            }
        ],
    },
}

CARD_REWARD_POOL = [card_id for card_id in CARD_LIBRARY.keys() if card_id not in STARTING_DECK]

RELIC_LIBRARY: Dict[str, Dict[str, Any]] = {
    "battle_battery": {
        "id": "battle_battery",
        "name": "Battle Battery",
        "icon": "⚡",
        "description": "At the start of each battle, gain 1 Energy.",
        "behaviors": [
            {
                "trigger": "onBattleStart",
                "effects": [
                    {"type": "gainEnergy", "amount": 1},
                    {"type": "log", "text": "{sourceName} crackles. Gain 1 Energy."},
                ],
            }
        ],
    },
    "thorn_sigil": {
        "id": "thorn_sigil",
        "name": "Thorn Sigil",
        "icon": "✶",
        "description": "Whenever you play a card, gain 1 Block.",
        "behaviors": [
            {
                "trigger": "onCardPlayed",
                "effects": [
                    {"type": "modifyStat", "target": "player", "stat": "block", "amount": 1},
                    {"type": "log", "text": "{sourceName} grants 1 Block."},
                ],
            }
        ],
    },
    "ember_idol": {
        "id": "ember_idol",
        "name": "Ember Idol",
        "icon": "🔥",
        "description": "At the start of your turn, gain 1 Strength.",
        "behaviors": [
            {
                "trigger": "onTurnStart",
                "effects": [
                    {"type": "modifyStat", "target": "player", "stat": "strength", "amount": 1},
                    {"type": "log", "text": "{sourceName} warms your blood. Gain 1 Strength."},
                ],
            }
        ],
    },
}

TREASURE_RELIC_POOL = list(RELIC_LIBRARY.keys())

CARD_ART = {
    "strike": {
        "title": "Strike",
        "image": "./src/assets/generated/cards/strike.png",
        "fallback": "./src/assets/player-placeholder.svg",
    },
    "defend": {
        "title": "Defend",
        "image": "./src/assets/generated/cards/defend.png",
        "fallback": "./src/assets/player-placeholder.svg",
    },
    "bash": {
        "title": "Bash",
        "image": "./src/assets/generated/cards/bash.png",
        "fallback": "./src/assets/generated/cards/strike.png",
    },
    "focus": {
        "title": "Focus",
        "image": "./src/assets/generated/cards/focus.png",
        "fallback": "./src/assets/enemy-placeholder.svg",
    },
    "quick_slash": {
        "title": "Quick Slash",
        "image": "./src/assets/generated/cards/quick_slash.png",
        "fallback": "./src/assets/generated/cards/strike.png",
    },
    "iron_shell": {
        "title": "Iron Shell",
        "image": "./src/assets/generated/cards/iron_shell.png",
        "fallback": "./src/assets/player-placeholder.svg",
    },
    "cleave": {
        "title": "Cleave",
        "image": "./src/assets/generated/cards/cleave.png",
        "fallback": "./src/assets/generated/cards/strike.png",
    },
    "second_wind": {
        "title": "Second Wind",
        "image": "./src/assets/generated/cards/second_wind.png",
        "fallback": "./src/assets/enemy-placeholder.svg",
    },
}

LEVEL_ART = {
    "n1": {
        "title": "Floor 1",
        "weaponName": "Scrapfang Shiv",
        "weaponDescription": "A jagged trench knife pieced together from rail scrap and scorched bone.",
        "weaponImage": "./src/assets/generated/n1-weapon.png",
        "enemyName": "Cinder Rat Brute",
        "enemyDescription": "A smoke-soaked tunnel predator with ember-lit eyes and furnace burns across its hide.",
        "enemyImage": "./src/assets/generated/n1-enemy.png",
    },
    "n2": {
        "title": "Floor 2",
        "weaponName": "Static Pike",
        "weaponDescription": "A long storm pike wound with cracked copper coils and a lightning focus at the tip.",
        "weaponImage": "./src/assets/generated/n2-weapon.png",
        "enemyName": "Lantern Stalker",
        "enemyDescription": "A thin ruin hunter draped in chains and carrying a poisoned lantern through the fog.",
        "enemyImage": "./src/assets/generated/n2-enemy.png",
    },
    "n3": {
        "title": "Floor 3",
        "weaponName": "Ashen Hookblade",
        "weaponDescription": "A hooked campfire blade blackened by soot, built for ripping armor in close quarters.",
        "weaponImage": "./src/assets/generated/n3-weapon.png",
        "enemyName": "Pyre Sentinel",
        "enemyDescription": "A dormant guardian formed from charcoal stone, still glowing with buried heat.",
        "enemyImage": "./src/assets/generated/n3-enemy.png",
    },
    "n4": {
        "title": "Floor 4",
        "weaponName": "Prism Cutter",
        "weaponDescription": "A relic dagger with a crystal edge that bends cold light into razor-thin arcs.",
        "weaponImage": "./src/assets/generated/n4-weapon.png",
        "enemyName": "Vault Mimic",
        "enemyDescription": "A treasure-chamber horror plated in gilded shells and jewel-like false eyes.",
        "enemyImage": "./src/assets/generated/n4-enemy.png",
    },
    "n5": {
        "title": "Floor 5",
        "weaponName": "Siegebreaker Maul",
        "weaponDescription": "A brutal bronze war maul ringed with impact runes and hydraulic braces.",
        "weaponImage": "./src/assets/generated/n5-weapon.png",
        "enemyName": "Bronze Husk Prime",
        "enemyDescription": "An elite war construct with cracked plating, molten seams, and a crushing frame.",
        "enemyImage": "./src/assets/generated/n5-enemy.png",
    },
    "n6": {
        "title": "Floor 6",
        "weaponName": "Neurolance",
        "weaponDescription": "A ceremonial spear built around a living crystal spine and pulsing neural filaments.",
        "weaponImage": "./src/assets/generated/n6-weapon.png",
        "enemyName": "The Neurolith",
        "enemyDescription": "A colossal psychic monolith suspended in cables, stone plates, and cold blue fire.",
        "enemyImage": "./src/assets/generated/n6-enemy.png",
    },
}

ENCOUNTERS = {
    "hallway": [
        {
            "enemies": [
                {
                    "name": "Ash Ghoul",
                    "maxHp": 42,
                    "intents": [
                        {"type": "attack", "value": 8, "label": "Claw 8"},
                        {"type": "buff", "strength": 2, "label": "Rage +2 Strength"},
                        {"type": "attackBlock", "value": 6, "block": 6, "label": "Rake 6 + Block 6"},
                    ],
                }
            ]
        },
        {
            "enemies": [
                {
                    "name": "Hollow Spear",
                    "maxHp": 38,
                    "intents": [
                        {"type": "attack", "value": 7, "label": "Lunge 7"},
                        {"type": "attack", "value": 7, "repeats": 2, "label": "Flurry 7x2"},
                        {"type": "debuff", "weak": 2, "label": "Pinning Curse"},
                    ],
                }
            ]
        },
        {
            "enemies": [
                {
                    "name": "Ash Ghoul",
                    "maxHp": 36,
                    "intents": [
                        {"type": "attack", "value": 6, "label": "Claw 6"},
                        {"type": "attackBlock", "value": 5, "block": 5, "label": "Rake 5 + Block 5"},
                    ],
                },
                {
                    "name": "Hollow Spear",
                    "maxHp": 30,
                    "intents": [
                        {"type": "attack", "value": 5, "label": "Lunge 5"},
                        {"type": "debuff", "weak": 1, "label": "Pinning Curse"},
                    ],
                },
            ]
        },
    ],
    "elite": [
        {
            "enemies": [
                {
                    "name": "Bronze Husk",
                    "maxHp": 68,
                    "intents": [
                        {"type": "attackBlock", "value": 10, "block": 8, "label": "Crush 10 + Block 8"},
                        {"type": "buff", "strength": 3, "label": "Harden +3 Strength"},
                        {"type": "attack", "value": 14, "label": "Hammerfall 14"},
                    ],
                },
                {
                    "name": "Shard Wisp",
                    "maxHp": 34,
                    "intents": [
                        {"type": "attack", "value": 6, "repeats": 2, "label": "Needle 6x2"},
                        {"type": "buff", "strength": 2, "label": "Flare +2 Strength"},
                    ],
                },
            ]
        }
    ],
    "boss": [
        {
            "enemies": [
                {
                    "name": "The Neurolith",
                    "maxHp": 120,
                    "intents": [
                        {"type": "attack", "value": 16, "label": "Pulse 16"},
                        {"type": "debuff", "vulnerable": 2, "weak": 2, "label": "Mind Fracture"},
                        {"type": "attack", "value": 12, "repeats": 2, "label": "Twin Surge 12x2"},
                        {
                            "type": "buff",
                            "strength": 4,
                            "block": 12,
                            "label": "Ascend +4 Strength +12 Block",
                        },
                    ],
                }
            ]
        }
    ],
}

MAP_TEMPLATE = [
    {"id": "n1", "type": "hallway", "label": "Hallway Fight"},
    {"id": "n2", "type": "hallway", "label": "Hallway Fight"},
    {"id": "n3", "type": "campfire", "label": "Campfire"},
    {"id": "n4", "type": "treasure", "label": "Treasure"},
    {"id": "n5", "type": "elite", "label": "Elite"},
    {"id": "n6", "type": "boss", "label": "Boss"},
]


# ── Session management ────────────────────────────────────────────────────────

class GameSession:
    def __init__(self, generated_run: Optional[Dict[str, Any]] = None) -> None:
        self.generated_run: Optional[Dict[str, Any]] = generated_run
        self.state: Dict[str, Any] = create_initial_state(generated_run)
        self.connections: set[WebSocket] = set()
        self.lock = asyncio.Lock()
        self.rng = random.Random()


games_state: Dict[int, GameSession] = {}
# Stores pending generated run data before a WebSocket session is created
pending_runs: Dict[int, Dict[str, Any]] = {}


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@router.websocket("/ws/{lobby_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    lobby_id: int,
    current_user: User = Depends(get_current_user),
):
    game_user = await GameCRUD.get_game_user(game_id=lobby_id, user_id=current_user.id)
    if not game_user:
        await websocket.close(code=4003)
        return

    await websocket.accept()

    session = games_state.get(lobby_id)
    if session is None:
        # Use LLM-generated run data if it was prepared in advance
        generated_run = pending_runs.pop(lobby_id, None)
        session = GameSession(generated_run=generated_run)
        games_state[lobby_id] = session

    session.connections.add(websocket)

    await websocket.send_json({"type": "state", "state": _public_state(session.state)})

    try:
        while True:
            data = await websocket.receive_json()
            await handle_client_message(session, websocket, data)
    except WebSocketDisconnect:
        pass
    finally:
        session.connections.discard(websocket)


@router.post("/generate/{lobby_id}")
async def generate_run_for_lobby(
    lobby_id: int,
    current_user: User = Depends(get_current_user),
):
    """
    Generate LLM content for a lobby before the WebSocket session starts.
    Call this after creating a new game (POST /lobby/new-game) and before
    connecting the WebSocket. The generated run is stored in pending_runs
    and picked up when the first WebSocket connection is made.

    Returns: {"status": "ok", "theme": "...", "imageGenerationStarted": true/false}
    """
    from app.llm_gen import generate_run
    from app.img_gen import generate_run_images

    # Verify the user belongs to this lobby
    game_user = await GameCRUD.get_game_user(game_id=lobby_id, user_id=current_user.id)
    if not game_user:
        raise HTTPException(status_code=403, detail="Not a member of this lobby.")

    # If a session already exists and is running, we can't regenerate it
    if lobby_id in games_state:
        raise HTTPException(status_code=409, detail="Game session already started. Cannot regenerate.")

    try:
        loop = asyncio.get_running_loop()
        generated_run = await loop.run_in_executor(None, generate_run)
    except Exception as exc:
        logger.error("LLM run generation failed for lobby %d: %s", lobby_id, exc)
        raise HTTPException(status_code=502, detail=f"LLM generation failed: {exc}")

    pending_runs[lobby_id] = generated_run

    # Start image generation in the background (non-blocking)
    image_prompts = generated_run.get("imagePrompts") or {}
    img_started = bool(image_prompts)
    if img_started:
        asyncio.create_task(
            generate_run_images(image_prompts),
            name=f"imggen-lobby-{lobby_id}",
        )

    return {
        "status": "ok",
        "theme": generated_run.get("theme", ""),
        "imageGenerationStarted": img_started,
    }


async def handle_client_message(session: GameSession, websocket: WebSocket, data: Dict[str, Any]) -> None:
    if not isinstance(data, dict):
        await websocket.send_json({"type": "error", "message": "Invalid payload."})
        return

    message_type = data.get("type")
    if message_type == "ping":
        await websocket.send_json({"type": "pong"})
        return

    if message_type == "get_state":
        await websocket.send_json({"type": "state", "state": _public_state(session.state)})
        return

    action = data.get("action")
    if not action and message_type == "action":
        action = data.get("action")

    if not action:
        await websocket.send_json({"type": "error", "message": "Missing action."})
        return

    action_id = data.get("id")

    async with session.lock:
        result = dispatch_action(session, action, action_id)
        if "error" in result:
            await websocket.send_json({"type": "error", "message": result["error"]})
            return
        payload = {
            "type": "state",
            "state": _public_state(session.state),
        }
        if result.get("fx"):
            payload["fx"] = result["fx"]
        if result.get("sfx"):
            payload["sfx"] = result["sfx"]

    await broadcast_state(session, payload)


def _public_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a copy of game state ready for the client.
    Strips internal keys and injects merged card/relic catalogs so the
    frontend can render LLM-generated cards without extra API calls.
    """
    s = copy.deepcopy(state)
    generated_run = s.pop("_generatedRun", None)

    # Build merged catalogs: static + generated (generated takes precedence)
    card_catalog: Dict[str, Any] = {}
    for cid, cdef in CARD_LIBRARY.items():
        card_catalog[cid] = {k: v for k, v in cdef.items() if k != "behaviors"}
    if generated_run:
        for cdef in (generated_run.get("cards") or []):
            cid = cdef.get("id")
            if cid:
                card_catalog[cid] = {k: v for k, v in cdef.items() if k != "behaviors"}

    relic_catalog: Dict[str, Any] = {}
    for rid, rdef in RELIC_LIBRARY.items():
        relic_catalog[rid] = {k: v for k, v in rdef.items() if k != "behaviors"}
    if generated_run:
        for rdef in (generated_run.get("relics") or []):
            rid = rdef.get("id")
            if rid:
                relic_catalog[rid] = {k: v for k, v in rdef.items() if k != "behaviors"}

    s["cardCatalog"] = card_catalog
    s["relicCatalog"] = relic_catalog
    return s


async def broadcast_state(session: GameSession, payload: Dict[str, Any]) -> None:
    dead: List[WebSocket] = []
    for ws in session.connections:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        session.connections.discard(ws)


# ── Game logic (ported from frontend) ────────────────────────────────────────


def _get_level_art_for_run(node_id: str, generated_run: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return level art from the generated run if available, else static LEVEL_ART."""
    if generated_run and generated_run.get("levelArt", {}).get(node_id):
        art = copy.deepcopy(generated_run["levelArt"][node_id])
    else:
        art = copy.deepcopy(get_level_art(node_id))

    if generated_run and generated_run.get("imagePrompts", {}).get(node_id):
        enemy_path = RUN_IMAGE_DIR / f"{node_id}-enemy.png"
        weapon_path = RUN_IMAGE_DIR / f"{node_id}-weapon.png"
        if enemy_path.exists():
            art["enemyImage"] = f"/src/assets/generated/run/{node_id}-enemy.png"
        if weapon_path.exists():
            art["weaponImage"] = f"/src/assets/generated/run/{node_id}-weapon.png"

    return art


def _get_encounters_for_run(battle_type: str, generated_run: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return encounter pool from the generated run if available, else static ENCOUNTERS."""
    if generated_run and generated_run.get("encounters", {}).get(battle_type):
        return generated_run["encounters"][battle_type]
    return ENCOUNTERS[battle_type]


def _get_card_reward_pool_for_run(deck: List[str], generated_run: Optional[Dict[str, Any]]) -> List[str]:
    """
    Return card IDs eligible for reward from the run's card pool.
    LLM cards are injected into a temporary library for the session.
    """
    if generated_run and generated_run.get("cards"):
        pool = [c["id"] for c in generated_run["cards"]]
    else:
        pool = list(CARD_REWARD_POOL)
    return [cid for cid in pool if cid not in deck or len(deck) > 9]


def _get_relic_pool_for_run(relics_held: List[str], generated_run: Optional[Dict[str, Any]]) -> List[str]:
    """Return available relic IDs from the run's relic pool."""
    if generated_run and generated_run.get("relics"):
        pool = [r["id"] for r in generated_run["relics"]]
    else:
        pool = list(TREASURE_RELIC_POOL)
    available = [r for r in pool if r not in relics_held]
    return available if available else pool


def _get_card_def(card_id: str, generated_run: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Look up a card definition, checking generated cards first."""
    if generated_run:
        for card in (generated_run.get("cards") or []):
            if card.get("id") == card_id:
                return card
    return CARD_LIBRARY.get(card_id)


def _get_relic_def(relic_id: str, generated_run: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Look up a relic definition, checking generated relics first."""
    if generated_run:
        for relic in (generated_run.get("relics") or []):
            if relic.get("id") == relic_id:
                return relic
    return RELIC_LIBRARY.get(relic_id)


def create_initial_state(generated_run: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    # Use LLM-generated map nodes if available, otherwise static template
    if generated_run and generated_run.get("mapNodes"):
        map_nodes = generated_run["mapNodes"]
    else:
        map_nodes = [
            {
                **node,
                "index": index,
                "completed": False,
                "available": index == 0,
            }
            for index, node in enumerate(MAP_TEMPLATE)
        ]

    theme = (generated_run or {}).get("theme", "")
    log_message = f"A new ascent begins — {theme}. Choose your route." if theme else "A new ascent begins. Choose your route."

    return {
        "screen": "map",
        "floor": 1,
        "mapNodes": map_nodes,
        "player": {
            "name": "Warden",
            "hp": 72,
            "maxHp": 72,
            "block": 0,
            "strength": 0,
            "weak": 0,
            "vulnerable": 0,
            "metallicize": 0,
            "energy": 3,
            "maxEnergy": 3,
            "deck": list(STARTING_DECK),
            "drawPile": [],
            "discardPile": [],
            "hand": [],
            "exhaustPile": [],
            "relics": [],
        },
        "pendingRelicRewardId": None,
        "enemies": [],
        "selectedEnemyId": None,
        "rewardOptions": [],
        "log": [log_message],
        "battle": None,
        "outcome": None,
        "loadout": _get_level_art_for_run("n1", generated_run),
        "cardAnimation": None,
        # Internal: not sent to client (stripped in broadcast_state)
        "_generatedRun": generated_run,
    }


def dispatch_action(session: GameSession, action: str, action_id: Optional[Any]) -> Dict[str, Any]:
    state = session.state
    fx: List[Dict[str, Any]] = []
    sfx: List[str] = []

    if action == "travel":
        travel_to_node(state, str(action_id) if action_id is not None else None, session.rng)
    elif action == "play-card":
        try:
            index = int(action_id)
        except (TypeError, ValueError):
            return {"error": "Invalid card index."}
        result = play_card(state, index, session.rng)
        if result:
            fx = result.get("fx", [])
            sfx = result.get("sfx", [])
    elif action == "select-enemy":
        if action_id is not None:
            select_enemy_target(state, str(action_id))
    elif action == "end-turn":
        result = end_turn(state, session.rng)
        if result:
            fx = result.get("fx", [])
            sfx = result.get("sfx", [])
    elif action == "claim-reward":
        if action_id is None:
            return {"error": "Missing reward id."}
        claim_reward(state, str(action_id))
    elif action == "skip-reward":
        state["rewardOptions"] = []
    elif action == "rest":
        rest_at_campfire(state)
        sfx = ["heal"]
    elif action == "take-relic":
        take_relic(state)
        sfx = ["buff"]
    elif action == "restart":
        # Keep the same generated run on restart so the theme stays consistent
        session.state = create_initial_state(session.generated_run)
    elif action == "toggle-sfx":
        # Server does not manage client audio toggles.
        pass
    else:
        return {"error": f"Unknown action: {action}"}

    return {"fx": fx, "sfx": sfx}


def get_level_art(node_id: str) -> Dict[str, Any]:
    return LEVEL_ART.get(
        node_id,
        {
            "title": "Unknown Floor",
            "weaponName": "Fallback Blade",
            "weaponDescription": "A placeholder weapon illustration.",
            "weaponImage": "./src/assets/player-placeholder.svg",
            "enemyName": "Unknown Enemy",
            "enemyDescription": "A placeholder enemy illustration.",
            "enemyImage": "./src/assets/enemy-placeholder.svg",
        },
    )


def get_card_art(card_id: str) -> Dict[str, Any]:
    return CARD_ART.get(
        card_id,
        {
            "title": "Card Art",
            "image": "./src/assets/player-placeholder.svg",
            "fallback": "./src/assets/player-placeholder.svg",
        },
    )


def has_keyword(definition: Dict[str, Any], keyword: str) -> bool:
    return keyword in (definition.get("keywords") or [])


def travel_to_node(state: Dict[str, Any], node_id: Optional[str], rng: random.Random) -> None:
    if node_id is None:
        return

    node = next((entry for entry in state["mapNodes"] if entry["id"] == node_id), None)
    if not node or not node.get("available") or node.get("completed"):
        return

    generated_run = state.get("_generatedRun")
    state["loadout"] = _get_level_art_for_run(node["id"], generated_run)
    state["floor"] = node["index"] + 1
    add_log(state, f"You enter {node['label']}.")

    if node["type"] in {"hallway", "elite", "boss"}:
        start_battle(state, node, rng)
        return
    if node["type"] == "campfire":
        state["screen"] = "campfire"
        return
    if node["type"] == "treasure":
        state["pendingRelicRewardId"] = pick_relic_reward(state, rng)
        state["screen"] = "treasure"


def start_battle(state: Dict[str, Any], node: Dict[str, Any], rng: random.Random) -> None:
    battle_type = node["type"]
    generated_run = state.get("_generatedRun")
    encounter_pool = _get_encounters_for_run(battle_type, generated_run)
    template = clone_pick(encounter_pool, rng)
    enemy_templates = template.get("enemies") or [template]
    art = _get_level_art_for_run(node["id"], generated_run)

    enemies: List[Dict[str, Any]] = []
    for index, enemy_template in enumerate(enemy_templates):
        enemy_id = f"enemy-{index}-{enemy_template['name'].lower().replace(' ', '-')}"
        enemies.append(
            {
                **enemy_template,
                "id": enemy_id,
                "hp": enemy_template["maxHp"],
                "block": 0,
                "strength": 0,
                "weak": 0,
                "vulnerable": 0,
                "intentIndex": 0,
                "intent": enemy_template["intents"][0],
                "art": art,
            }
        )

    state["enemies"] = enemies
    state["selectedEnemyId"] = enemies[0]["id"] if enemies else None

    player = state["player"]
    player["block"] = 0
    player["energy"] = player["maxEnergy"]
    player["drawPile"] = shuffle(player["deck"], rng)
    player["discardPile"] = []
    player["hand"] = []
    player["exhaustPile"] = []
    player["weak"] = 0
    player["vulnerable"] = 0

    state["screen"] = "battle"
    state["battle"] = {"type": battle_type, "nodeId": node["id"]}
    state["loadout"] = art

    trigger_relic_event(state, "onBattleStart", battle_context(state, rng))
    draw_cards(state, 5, rng)
    add_log(state, f"{describe_encounter_headline(state)} appear.")


def play_card(state: Dict[str, Any], index: int, rng: random.Random) -> Optional[Dict[str, Any]]:
    if state["screen"] != "battle" or state.get("outcome"):
        return None

    hand = state["player"]["hand"]
    if index < 0 or index >= len(hand):
        return None

    card_id = hand[index]
    card = _get_card_def(card_id, state.get("_generatedRun"))
    if not card or card.get("cost", 0) > state["player"]["energy"]:
        return None

    state["player"]["energy"] -= card["cost"]
    hand.pop(index)

    feedback = build_card_feedback(card, state)

    trigger_card_event(state, card, "onPlay", battle_context(state, rng, card))
    trigger_relic_event(state, "onCardPlayed", battle_context(state, rng, card))

    state["cardAnimation"] = create_card_animation(card_id, card)

    if has_keyword(card, "exhaust"):
        state["player"]["exhaustPile"].append(card_id)
    else:
        state["player"]["discardPile"].append(card_id)

    process_defeated_enemies(state)
    if not state["enemies"]:
        win_battle(state, rng)
        return {"fx": feedback["fx"], "sfx": list(dict.fromkeys(feedback["sfx"] + ["victory"]))}

    return feedback


def select_enemy_target(state: Dict[str, Any], enemy_id: str) -> None:
    if state["screen"] != "battle":
        return

    enemy = next((entry for entry in state["enemies"] if entry["id"] == enemy_id and entry["hp"] > 0), None)
    if not enemy:
        return

    state["selectedEnemyId"] = enemy["id"]


def end_turn(state: Dict[str, Any], rng: random.Random) -> Optional[Dict[str, Any]]:
    if state["screen"] != "battle" or state.get("outcome"):
        return None

    trigger_relic_event(state, "onTurnEnd", battle_context(state, rng))

    state["player"]["discardPile"].extend(state["player"]["hand"])
    state["player"]["hand"] = []

    intent_result = run_enemy_intent(state)
    if state.get("outcome") == "defeat":
        trigger_relic_event(state, "onBattleEnd", {**battle_context(state, rng), "result": "defeat"})
        sfx = (intent_result or {}).get("sfx", []) + ["defeat"]
        return {"fx": (intent_result or {}).get("fx", []), "sfx": sfx}

    state["player"]["block"] = state["player"].get("metallicize", 0)
    state["player"]["energy"] = state["player"]["maxEnergy"]

    trigger_relic_event(state, "onTurnStart", battle_context(state, rng))
    tick_down_status(state["player"])

    for enemy in state["enemies"]:
        tick_down_status(enemy)
        advance_enemy_intent(enemy)

    draw_cards(state, 5, rng)

    for enemy in state["enemies"]:
        add_log(state, f"{enemy['name']} prepares {enemy['intent']['label']}.")

    return intent_result or {"fx": [], "sfx": []}


def run_enemy_intent(state: Dict[str, Any]) -> Dict[str, Any]:
    fx_events: List[Dict[str, Any]] = []
    sfx_list: List[str] = []

    for enemy in state["enemies"]:
        intent = enemy.get("intent")
        if not intent:
            continue

        if intent["type"] in {"attack", "attackBlock"}:
            repeats = intent.get("repeats", 1)
            for _ in range(repeats):
                damage = adjusted_damage(
                    intent["value"] + enemy.get("strength", 0),
                    enemy.get("weak", 0),
                    state["player"].get("vulnerable", 0),
                )
                absorb_damage(state["player"], damage)
                add_log(state, f"{enemy['name']} hits for {damage}.")
                fx_events.append({"type": "damage", "target": "player:0", "value": damage})
                sfx_list.append("enemyAttack")
                if state["player"]["hp"] <= 0:
                    state["outcome"] = "defeat"
                    state["screen"] = "map"
                    return {"fx": fx_events, "sfx": sfx_list}

        if intent["type"] == "attackBlock" and intent.get("block"):
            enemy["block"] += intent["block"]
            fx_events.append(
                {"type": "block", "target": get_enemy_fx_target(state, enemy["id"]), "value": intent["block"]}
            )
            sfx_list.append("block")

        if intent["type"] == "buff":
            enemy["strength"] += intent.get("strength", 0)
            enemy["block"] += intent.get("block", 0)
            add_log(state, f"{enemy['name']} grows stronger.")
            fx_events.append(
                {"type": "buff", "target": get_enemy_fx_target(state, enemy["id"]), "label": intent.get("label")}
            )
            sfx_list.append("buff")

        if intent["type"] == "debuff":
            state["player"]["weak"] += intent.get("weak", 0)
            state["player"]["vulnerable"] += intent.get("vulnerable", 0)
            add_log(state, f"{enemy['name']} curses your footing.")
            fx_events.append({"type": "debuff", "target": "player:0", "label": intent.get("label")})
            sfx_list.append("debuff")

    return {"fx": fx_events, "sfx": sfx_list}


def win_battle(state: Dict[str, Any], rng: random.Random) -> None:
    add_log(state, "The encounter is cleared.")
    state["enemies"] = []
    state["selectedEnemyId"] = None
    state["player"]["block"] = 0
    state["player"]["energy"] = state["player"]["maxEnergy"]
    state["rewardOptions"] = pick_reward_cards(state["player"]["deck"], rng, state.get("_generatedRun"))
    state["screen"] = "map"
    state["mapNodes"][state["floor"] - 1]["completed"] = True
    unlock_next_node(state)
    trigger_relic_event(state, "onBattleEnd", {**battle_context(state, rng), "result": "victory"})

    if state.get("battle", {}).get("type") == "boss":
        state["outcome"] = "victory"
        state["screen"] = "map"


def claim_reward(state: Dict[str, Any], card_id: str) -> None:
    state["player"]["deck"].append(card_id)
    card_def = _get_card_def(card_id, state.get("_generatedRun"))
    card_name = card_def["name"] if card_def else card_id
    add_log(state, f"You add {card_name} to your deck.")
    state["rewardOptions"] = []
    state["screen"] = "map"


def rest_at_campfire(state: Dict[str, Any]) -> None:
    player = state["player"]
    player["hp"] = min(player["maxHp"], player["hp"] + 16)
    add_log(state, "You rest at the fire and recover 16 HP.")
    complete_current_node(state)
    state["screen"] = "map"


def take_relic(state: Dict[str, Any]) -> None:
    relic_id = state.get("pendingRelicRewardId")
    if relic_id:
        grant_relic(state, relic_id)
    complete_current_node(state)
    state["pendingRelicRewardId"] = None
    state["screen"] = "map"


def unlock_next_node(state: Dict[str, Any]) -> None:
    next_node = state["mapNodes"][state["floor"] : state["floor"] + 1]
    if next_node:
        next_node[0]["available"] = True


def complete_current_node(state: Dict[str, Any]) -> None:
    node = state["mapNodes"][state["floor"] - 1] if state["floor"] - 1 < len(state["mapNodes"]) else None
    if not node:
        return
    node["completed"] = True
    unlock_next_node(state)


# ── FX/SFX feedback helpers ──────────────────────────────────────────────────


def build_card_feedback(card: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    feedback = {"fx": [], "sfx": ["cardPlay"]}
    for behavior in card.get("behaviors", []):
        if behavior.get("trigger") != "onPlay":
            continue
        collect_effect_feedback(behavior.get("effects", []), state, feedback)

    # Unique SFX list
    feedback["sfx"] = list(dict.fromkeys(feedback["sfx"]))
    return feedback


def collect_effect_feedback(effects: List[Dict[str, Any]], state: Dict[str, Any], feedback: Dict[str, Any]) -> None:
    for effect in effects:
        if not effect or not effect.get("type"):
            continue

        if effect["type"] == "repeat":
            collect_effect_feedback(effect.get("effects", []), state, feedback)
            continue

        if effect["type"] == "condition":
            collect_effect_feedback(effect.get("effects", []), state, feedback)
            collect_effect_feedback(effect.get("elseEffects", []), state, feedback)
            continue

        if effect["type"] == "damage":
            targets = get_fx_targets_for_effect(state, effect.get("target"))
            for target in targets:
                feedback["fx"].append(
                    {"type": "damage", "target": target, "value": resolve_fx_value(state, effect)}
                )
            feedback["sfx"].append("attack")
            continue

        if effect["type"] == "heal":
            targets = get_fx_targets_for_effect(state, effect.get("target"))
            for target in targets:
                feedback["fx"].append(
                    {"type": "heal", "target": target, "value": resolve_fx_value(state, effect)}
                )
            feedback["sfx"].append("heal")
            continue

        if effect["type"] == "modifyStat":
            targets = get_fx_targets_for_effect(state, effect.get("target"))
            is_debuff = effect.get("stat") in {"weak", "vulnerable"}
            fx_type = "block" if effect.get("stat") == "block" else "debuff" if is_debuff else "buff"
            for target in targets:
                payload = {"type": fx_type, "target": target}
                if fx_type == "block":
                    payload["value"] = resolve_fx_value(state, effect)
                else:
                    payload["label"] = format_stat_label(effect.get("stat"), resolve_fx_value(state, effect))
                feedback["fx"].append(payload)
            feedback["sfx"].append("block" if fx_type == "block" else "debuff" if is_debuff else "buff")
            continue

        if effect["type"] == "gainEnergy":
            feedback["sfx"].append("buff")
            continue

        if effect["type"] == "drawCards":
            feedback["sfx"].append("cardPlay")
            continue


def get_fx_targets_for_effect(state: Dict[str, Any], target: Optional[str]) -> List[str]:
    if target in {"self", "owner", "player"}:
        return ["player:0"]
    if target == "allEnemies":
        return [get_enemy_fx_target(state, enemy["id"]) for enemy in state["enemies"]]
    return [get_enemy_fx_target(state, state.get("selectedEnemyId"))]


def get_enemy_fx_target(state: Dict[str, Any], enemy_id: Optional[str]) -> str:
    enemies = state.get("enemies", [])
    index = next((i for i, enemy in enumerate(enemies) if enemy["id"] == enemy_id), -1)
    fallback_index = next((i for i, enemy in enumerate(enemies) if enemy.get("hp", 0) > 0), -1)
    resolved_index = index if index >= 0 else max(0, fallback_index)
    return f"enemy:{resolved_index}"


def resolve_fx_value(state: Dict[str, Any], effect: Dict[str, Any]) -> int:
    amount = effect.get("amount")
    if isinstance(amount, int):
        if effect.get("type") == "damage" and effect.get("useCombatModifiers"):
            target_id = state.get("selectedEnemyId")
            if effect.get("target") == "allEnemies":
                target_id = state["enemies"][0]["id"] if state["enemies"] else None
            target = next((enemy for enemy in state["enemies"] if enemy["id"] == target_id), None)
            return adjusted_damage(
                amount + state["player"].get("strength", 0),
                state["player"].get("weak", 0),
                (target or {}).get("vulnerable", 0),
            )
        return amount
    if amount == "playerStrength":
        return state["player"].get("strength", 0)
    if amount == "cardsInHand":
        return len(state["player"].get("hand", []))
    return 0


def format_stat_label(stat: Optional[str], amount: int) -> str:
    readable = (stat or "").replace("_", " ")
    return f"{amount:+d} {readable}"


def adjusted_damage(amount: int, weak: int, target_vulnerable: int) -> int:
    total = amount
    if weak > 0:
        total = int(total * 0.75)
    if target_vulnerable > 0:
        total = int(total * 1.5)
    return max(0, total)


def absorb_damage(target: Dict[str, Any], damage: int) -> None:
    blocked = min(target.get("block", 0), damage)
    target["block"] -= blocked
    target["hp"] -= damage - blocked


def process_defeated_enemies(state: Dict[str, Any]) -> None:
    defeated = [enemy for enemy in state["enemies"] if enemy.get("hp", 0) <= 0]
    for enemy in defeated:
        add_log(state, f"{enemy['name']} falls.")
    state["enemies"] = [enemy for enemy in state["enemies"] if enemy.get("hp", 0) > 0]
    if not any(enemy["id"] == state.get("selectedEnemyId") for enemy in state["enemies"]):
        state["selectedEnemyId"] = state["enemies"][0]["id"] if state["enemies"] else None


def tick_down_status(unit: Dict[str, Any]) -> None:
    unit["weak"] = max(0, unit.get("weak", 0) - 1)
    unit["vulnerable"] = max(0, unit.get("vulnerable", 0) - 1)


def advance_enemy_intent(enemy: Dict[str, Any]) -> None:
    enemy["intentIndex"] = (enemy.get("intentIndex", 0) + 1) % len(enemy.get("intents", []))
    enemy["intent"] = enemy.get("intents", [])[enemy["intentIndex"]]


def draw_cards(state: Dict[str, Any], amount: int, rng: random.Random) -> None:
    for _ in range(amount):
        if not state["player"]["drawPile"]:
            if not state["player"]["discardPile"]:
                return
            state["player"]["drawPile"] = shuffle(state["player"]["discardPile"], rng)
            state["player"]["discardPile"] = []

        next_card_id = state["player"]["drawPile"].pop() if state["player"]["drawPile"] else None
        if not next_card_id:
            continue
        card = _get_card_def(next_card_id, state.get("_generatedRun"))
        state["player"]["hand"].append(next_card_id)
        if card:
            trigger_card_event(state, card, "onDraw", battle_context(state, rng, card))
            trigger_relic_event(state, "onCardDrawn", battle_context(state, rng, card))


def pick_reward_cards(deck: List[str], rng: random.Random, generated_run: Optional[Dict[str, Any]] = None) -> List[str]:
    pool = _get_card_reward_pool_for_run(deck, generated_run)
    return shuffle(pool, rng)[:3]


def pick_relic_reward(state: Dict[str, Any], rng: random.Random) -> str:
    generated_run = state.get("_generatedRun")
    pool = _get_relic_pool_for_run(state["player"]["relics"], generated_run)
    if not pool:
        pool = list(TREASURE_RELIC_POOL)
    return pool[rng.randrange(0, len(pool))]


def grant_relic(state: Dict[str, Any], relic_id: str) -> None:
    relic = _get_relic_def(relic_id, state.get("_generatedRun"))
    if not relic:
        return
    if relic_id not in state["player"]["relics"]:
        state["player"]["relics"].append(relic_id)
    add_log(state, f"You claim {relic['name']}.")


def battle_context(state: Dict[str, Any], rng: random.Random, card: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "state": state,
        "card": card,
        "targetEnemyId": state.get("selectedEnemyId"),
        "absorbDamage": absorb_damage,
        "drawCards": lambda s, amount: draw_cards(s, amount, rng),
    }


def add_log(state: Dict[str, Any], message: str) -> None:
    state["log"].insert(0, message)


def describe_encounter_headline(state: Dict[str, Any]) -> str:
    if not state["enemies"]:
        return "No active enemy"
    if len(state["enemies"]) == 1:
        return state["enemies"][0]["name"]
    return f"{len(state['enemies'])} Enemies"


def create_card_animation(card_id: str, card: Dict[str, Any]) -> Dict[str, Any]:
    art = get_card_art(card_id)
    return {
        "id": f"{card_id}-{int(time.time() * 1000)}",
        "image": art["image"],
        "fallback": art["fallback"],
        "name": card["name"],
        "type": card["type"],
        "variant": "attack-cast" if card.get("type") == "Attack" else "skill-cast",
    }


def shuffle(items: List[str], rng: random.Random) -> List[str]:
    array = list(items)
    for index in range(len(array) - 1, 0, -1):
        swap_index = rng.randrange(0, index + 1)
        array[index], array[swap_index] = array[swap_index], array[index]
    return array


def clone_pick(items: List[Dict[str, Any]], rng: random.Random) -> Dict[str, Any]:
    return copy.deepcopy(items[rng.randrange(0, len(items))])


# ── Effect engine (ported from frontend) ─────────────────────────────────────


def trigger_relic_event(state: Dict[str, Any], trigger: str, context: Optional[Dict[str, Any]] = None) -> None:
    context = context or {}
    generated_run = state.get("_generatedRun")
    for relic_id in state["player"]["relics"]:
        relic = _get_relic_def(relic_id, generated_run)
        if not relic:
            continue
        run_behavior_set(state, relic.get("behaviors", []), trigger, {
            **context,
            "owner": "player",
            "source": relic,
            "sourceType": "relic",
        })


def trigger_card_event(state: Dict[str, Any], card: Dict[str, Any], trigger: str, context: Optional[Dict[str, Any]] = None) -> None:
    context = context or {}
    run_behavior_set(state, card.get("behaviors", []), trigger, {
        **context,
        "owner": "player",
        "source": card,
        "sourceType": "card",
        "card": card,
    })


def run_behavior_set(state: Dict[str, Any], behaviors: List[Dict[str, Any]], trigger: str, context: Dict[str, Any]) -> None:
    for behavior in behaviors or []:
        if behavior.get("trigger") != trigger:
            continue
        execute_effects(state, behavior.get("effects", []), context)


def execute_effects(state: Dict[str, Any], effects: List[Dict[str, Any]], context: Dict[str, Any]) -> None:
    for effect in effects or []:
        execute_effect(state, effect, context)


def execute_effect(state: Dict[str, Any], effect: Dict[str, Any], context: Dict[str, Any]) -> None:
    if not effect or not effect.get("type"):
        return

    if effect["type"] == "repeat":
        times = resolve_numeric_value(effect.get("times"), state, context)
        for index in range(times):
            execute_effects(state, effect.get("effects", []), {**context, "repeatIndex": index})
        return

    if effect["type"] == "condition":
        passed = evaluate_condition(state, effect.get("condition"), context)
        execute_effects(state, effect.get("effects") if passed else effect.get("elseEffects"), context)
        return

    if effect["type"] == "log":
        state["log"].insert(0, interpolate_text(effect.get("text", ""), state, context))
        return

    if effect["type"] == "drawCards":
        draw_fn = context.get("drawCards")
        if draw_fn:
            draw_fn(state, resolve_numeric_value(effect.get("amount"), state, context))
        return

    if effect["type"] == "gainEnergy":
        state["player"]["energy"] += resolve_numeric_value(effect.get("amount"), state, context)
        return

    if effect["type"] == "heal":
        targets = resolve_target_units(state, effect.get("target"), context)
        if not targets:
            return
        amount = resolve_numeric_value(effect.get("amount"), state, context)
        for target in targets:
            target["hp"] = min(target["maxHp"], target["hp"] + amount)
        return

    if effect["type"] == "modifyStat":
        targets = resolve_target_units(state, effect.get("target"), context)
        if not targets:
            return
        amount = resolve_numeric_value(effect.get("amount"), state, context)
        for target in targets:
            target[effect["stat"]] = target.get(effect["stat"], 0) + amount
        return

    if effect["type"] == "damage":
        targets = resolve_target_units(state, effect.get("target"), context)
        if not targets:
            return
        attacker = resolve_target_unit(state, effect.get("sourceTarget", "self"), context)
        amount = resolve_numeric_value(effect.get("amount"), state, context)
        for target in targets:
            resolved_amount = amount
            if effect.get("useCombatModifiers") and attacker:
                resolved_amount = calculate_damage_with_modifiers(amount, attacker, target)
            absorb_fn = context.get("absorbDamage")
            if absorb_fn:
                absorb_fn(target, resolved_amount)
        return

    if effect["type"] == "addCard":
        zone = effect.get("zone", "discardPile")
        amount = resolve_numeric_value(effect.get("amount", 1), state, context)
        for _ in range(amount):
            state["player"][zone].append(effect.get("cardId"))


def evaluate_condition(state: Dict[str, Any], condition: Optional[Dict[str, Any]], context: Dict[str, Any]) -> bool:
    if not condition:
        return True

    target = resolve_target_unit(state, condition.get("target"), context)
    if not target:
        return False

    current = target.get(condition.get("stat"))
    if current is None:
        return False
    value = resolve_numeric_value(condition.get("value"), state, context)

    if condition.get("operator") == "gt":
        return current > value
    if condition.get("operator") == "gte":
        return current >= value
    if condition.get("operator") == "lt":
        return current < value
    if condition.get("operator") == "lte":
        return current <= value
    if condition.get("operator") == "eq":
        return current == value
    return False


def resolve_numeric_value(value: Any, state: Dict[str, Any], context: Dict[str, Any]) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        if value == "cardsInHand":
            return len(state["player"].get("hand", []))
        if value == "playerStrength":
            return state["player"].get("strength", 0)
    return 0


def resolve_target_units(state: Dict[str, Any], target: Optional[str], context: Dict[str, Any]) -> List[Dict[str, Any]]:
    if target == "allEnemies":
        return get_alive_enemies(state)

    unit = resolve_target_unit(state, target, context)
    return [unit] if unit else []


def resolve_target_unit(state: Dict[str, Any], target: Optional[str], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if target == "player":
        return state["player"]
    if target == "enemy":
        return get_primary_enemy(state, context)
    if target in {"self", "owner"}:
        return get_primary_enemy(state, context) if context.get("owner") == "enemy" else state["player"]
    if target == "opponent":
        return state["player"] if context.get("owner") == "enemy" else get_primary_enemy(state, context)
    return None


def get_primary_enemy(state: Dict[str, Any], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if context.get("targetEnemyId"):
        return next(
            (enemy for enemy in get_alive_enemies(state) if enemy["id"] == context.get("targetEnemyId")),
            get_alive_enemies(state)[0] if get_alive_enemies(state) else None,
        )
    return get_alive_enemies(state)[0] if get_alive_enemies(state) else None


def get_alive_enemies(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [enemy for enemy in state.get("enemies", []) if enemy.get("hp", 0) > 0]


def calculate_damage_with_modifiers(amount: int, attacker: Dict[str, Any], defender: Dict[str, Any]) -> int:
    total = amount + attacker.get("strength", 0)
    if attacker.get("weak", 0) > 0:
        total = int(total * 0.75)
    if defender.get("vulnerable", 0) > 0:
        total = int(total * 1.5)
    return max(0, total)


def interpolate_text(text: str, state: Dict[str, Any], context: Dict[str, Any]) -> str:
    enemy_name = get_alive_enemies(state)[0]["name"] if get_alive_enemies(state) else "enemy"
    return (
        text.replace("{playerName}", state["player"].get("name", ""))
        .replace("{enemyName}", enemy_name)
        .replace("{sourceName}", (context.get("source") or {}).get("name", "Effect"))
        .replace("{cardName}", (context.get("card") or {}).get("name", ""))
    )


def describe_relic(relic_id: str) -> Optional[Dict[str, Any]]:
    return RELIC_LIBRARY.get(relic_id)


def describe_card(card_id: str) -> Optional[Dict[str, Any]]:
    return CARD_LIBRARY.get(card_id)
