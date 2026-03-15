import { CARD_LIBRARY, CARD_REWARD_POOL, STARTING_DECK } from "./data/cards.js";
import { RELIC_LIBRARY, TREASURE_RELIC_POOL } from "./data/relics.js";
import {
  describeRelic,
  hasKeyword,
  triggerCardEvent,
  triggerRelicEvent,
} from "./effectEngine.js";
import { triggerFx } from "./fx.js";
import { playSfx, SFX } from "./sfx.js";
import { getCardArt } from "./cardArt.js";
import { getLevelArt } from "./levelArt.js";

const ENCOUNTERS = {
  hallway: [
    {
      enemies: [
        {
          name: "Ash Ghoul",
          maxHp: 42,
          intents: [
            { type: "attack", value: 8, label: "Claw 8" },
            { type: "buff", strength: 2, label: "Rage +2 Strength" },
            { type: "attackBlock", value: 6, block: 6, label: "Rake 6 + Block 6" },
          ],
        },
      ],
    },
    {
      enemies: [
        {
          name: "Hollow Spear",
          maxHp: 38,
          intents: [
            { type: "attack", value: 7, label: "Lunge 7" },
            { type: "attack", value: 7, repeats: 2, label: "Flurry 7x2" },
            { type: "debuff", weak: 2, label: "Pinning Curse" },
          ],
        },
      ],
    },
    {
      enemies: [
        {
          name: "Ash Ghoul",
          maxHp: 36,
          intents: [
            { type: "attack", value: 6, label: "Claw 6" },
            { type: "attackBlock", value: 5, block: 5, label: "Rake 5 + Block 5" },
          ],
        },
        {
          name: "Hollow Spear",
          maxHp: 30,
          intents: [
            { type: "attack", value: 5, label: "Lunge 5" },
            { type: "debuff", weak: 1, label: "Pinning Curse" },
          ],
        },
      ],
    },
  ],
  elite: [
    {
      enemies: [
        {
          name: "Bronze Husk",
          maxHp: 68,
          intents: [
            { type: "attackBlock", value: 10, block: 8, label: "Crush 10 + Block 8" },
            { type: "buff", strength: 3, label: "Harden +3 Strength" },
            { type: "attack", value: 14, label: "Hammerfall 14" },
          ],
        },
        {
          name: "Shard Wisp",
          maxHp: 34,
          intents: [
            { type: "attack", value: 6, repeats: 2, label: "Needle 6x2" },
            { type: "buff", strength: 2, label: "Flare +2 Strength" },
          ],
        },
      ],
    },
  ],
  boss: [
    {
      enemies: [
        {
          name: "The Neurolith",
          maxHp: 120,
          intents: [
            { type: "attack", value: 16, label: "Pulse 16" },
            { type: "debuff", vulnerable: 2, weak: 2, label: "Mind Fracture" },
            { type: "attack", value: 12, repeats: 2, label: "Twin Surge 12x2" },
            { type: "buff", strength: 4, block: 12, label: "Ascend +4 Strength +12 Block" },
          ],
        },
      ],
    },
  ],
};

const MAP_TEMPLATE = [
  { id: "n1", type: "hallway", label: "Hallway Fight" },
  { id: "n2", type: "hallway", label: "Hallway Fight" },
  { id: "n3", type: "campfire", label: "Campfire" },
  { id: "n4", type: "treasure", label: "Treasure" },
  { id: "n5", type: "elite", label: "Elite" },
  { id: "n6", type: "boss", label: "Boss" },
];

export function mountApp(root) {
  if (!root) {
    return;
  }

  const state = createInitialState();
  let animationTimeoutId = null;

  function setState(mutator) {
    mutator(state);
    render();
  }

  function render() {
    root.innerHTML = renderApp(state);
    bindEvents();
  }

  function bindEvents() {
    for (const button of root.querySelectorAll("[data-action]")) {
      button.addEventListener("click", () => handleAction(button.dataset.action, button.dataset.id));
    }
  }

  function handleAction(action, id) {
    if (action === "travel") {
      setState((draft) => travelToNode(draft, id));
      return;
    }

    if (action === "play-card") {
      // [FX] [SFX] Capture fx/sfx events from card result before re-render
      let fxEvents = [];
      let sfxList  = [];

      setState((draft) => {
        const result = playCard(draft, Number(id));
        if (result) { fxEvents = result.fx; sfxList = result.sfx; }
      });

      // [SFX] Play sounds (user-gesture context, no autoplay block)
      for (const s of sfxList) playSfx(s);

      // [FX] Fire visuals after render has settled (triggerFx uses rAF internally)
      triggerFx(fxEvents);
      scheduleCardAnimationCleanup();
      return;
    }

    if (action === "select-enemy") {
      setState((draft) => selectEnemyTarget(draft, id));
      return;
    }

    if (action === "end-turn") {
      // [FX] [SFX] Capture enemy-intent fx/sfx events
      let fxEvents = [];
      let sfxList  = [];

      setState((draft) => {
        const result = endTurn(draft);
        if (result) { fxEvents = result.fx; sfxList = result.sfx; }
      });

      for (const s of sfxList) playSfx(s);
      triggerFx(fxEvents);
      return;
    }

    if (action === "claim-reward") {
      setState((draft) => claimReward(draft, id));
      return;
    }

    if (action === "skip-reward") {
      setState((draft) => {
        draft.rewardOptions = [];
      });
      return;
    }

    if (action === "rest") {
      setState((draft) => {
        draft.player.hp = Math.min(draft.player.maxHp, draft.player.hp + 16);
        addLog(draft, "You rest at the fire and recover 16 HP.");
        completeCurrentNode(draft);
        draft.screen = "map";
      });
      // [SFX]
      playSfx("heal");
      return;
    }

    if (action === "take-relic") {
      setState((draft) => {
        grantRelic(draft, draft.pendingRelicRewardId);
        completeCurrentNode(draft);
        draft.pendingRelicRewardId = null;
        draft.screen = "map";
      });
      // [SFX]
      playSfx("buff");
      return;
    }

    // [SFX] Sound toggle button — no state mutation needed
    if (action === "toggle-sfx") { // [SFX]
      SFX.toggle();
      render(); // re-render to update button label
      return;
    }

    if (action === "restart") {
      Object.assign(state, createInitialState());
      render();
    }
  }

  render();

  function scheduleCardAnimationCleanup() {
    if (!state.cardAnimation) {
      return;
    }

    if (animationTimeoutId) {
      clearTimeout(animationTimeoutId);
    }

    animationTimeoutId = window.setTimeout(() => {
      state.cardAnimation = null;
      render();
    }, 720);
  }
}

function createInitialState() {
  return {
    screen: "map",
    floor: 1,
    mapNodes: MAP_TEMPLATE.map((node, index) => ({
      ...node,
      index,
      completed: false,
      available: index === 0,
    })),
    player: {
      name: "Warden",
      hp: 72,
      maxHp: 72,
      block: 0,
      strength: 0,
      weak: 0,
      vulnerable: 0,
      metallicize: 0,
      energy: 3,
      maxEnergy: 3,
      deck: [...STARTING_DECK],
      drawPile: [],
      discardPile: [],
      hand: [],
      exhaustPile: [],
      relics: [],
    },
    pendingRelicRewardId: null,
    enemies: [],
    selectedEnemyId: null,
    rewardOptions: [],
    log: ["A new ascent begins. Choose your route."],
    battle: null,
    outcome: null,
    loadout: getLevelArt("n1"),
    cardAnimation: null,
  };
}

function renderApp(state) {
  return `
    <div class="spire-app">
      <main class="stage full-stage">
        ${renderTopBar(state)}
        ${state.screen === "battle" ? renderBattle(state) : `${renderNonBattle(state)}${renderDeckStrip(state)}`}
      </main>
      ${renderOverlay(state)}
    </div>
  `;
}

function renderNode(node, state) {
  const current = state.mapNodes.find((entry) => entry.available && !entry.completed);
  const isNext = current?.id === node.id;
  const disabled = !node.available || node.completed || state.screen === "battle";
  return `
    <button class="node-card ${isNext ? "active" : ""}" data-action="travel" data-id="${node.id}" ${disabled ? "disabled" : ""}>
      <span class="node-icon">${nodeGlyph(node.type)}</span>
      <strong>${node.label}</strong>
      <p class="muted">Floor ${node.index + 1}</p>
      <p>${node.completed ? "Cleared" : node.available ? "Available" : "Locked"}</p>
    </button>
  `;
}

function renderTopBar(state) {
  return `
    <section class="top-bar">
      <div class="top-pill">
        <p class="eyebrow">Run</p>
        <h3>Neuroslope Spire</h3>
        <p class="muted">Floor ${state.floor} | ${state.screen === "battle" ? "In combat" : "Planning route"}</p>
      </div>
      <div class="top-pill">
        <p class="eyebrow">${state.player.name}</p>
        <h3>HP ${state.player.hp}/${state.player.maxHp}</h3>
        <p class="muted">Energy ${state.player.energy}/${state.player.maxEnergy} | Relics ${state.player.relics.length}</p>
      </div>
      <div class="top-pill">
        <p class="eyebrow">Encounter</p>
        <h3>${describeEncounterHeadline(state)}</h3>
        <p class="muted">${state.enemies.length > 0 ? "Battle in progress" : "Choose the next room on the map."}</p>
        <button class="button-muted topbar-toggle" data-action="toggle-sfx">
          ${SFX.enabled ? "🔊 Sound on" : "🔇 Sound off"}
        </button>
      </div>
    </section>
  `;
}

function renderBattle(state) {
  return `
    <section class="spire-battle-layout">
      <section class="battle-scene">
        ${renderCardAnimation(state.cardAnimation)}
        <div class="player-side combatant" data-combatant="player-0">
          <div class="combatant-frame player-frame">
            <div class="player-loadout">
              <img class="portrait" src="./src/assets/player-placeholder.svg" alt="${state.player.name}" />
              ${renderCombatFooter(state.player, "player")}
            </div>
          </div>
        </div>
        <div class="enemy-side">
          ${state.enemies.map((enemy, index) => renderEnemy(enemy, state.selectedEnemyId, index)).join("")}
        </div>
      </section>
      <section class="battle-hud">
        <div class="hand-panel">
          <div class="hand-shell">
            <div class="hand-row">
              ${state.player.hand.map((cardId, index) => renderCard(cardId, state, index)).join("")}
            </div>
          </div>
        </div>
        <div class="battle-sidepanel">
          <p class="eyebrow">Turn</p>
          <div class="turn-energy">
            <h3>Energy ${state.player.energy}/${state.player.maxEnergy}</h3>
            <div class="energy-orb ${state.player.energy === 0 ? "empty" : ""}" aria-label="Current energy">
              <span>${state.player.energy}</span>
            </div>
          </div>
          <p class="muted">Hand ${state.player.hand.length}</p>
          <button class="button-primary end-turn-button" data-action="end-turn">End Turn</button>
        </div>
      </section>
    </section>
  `;
}

function renderCardAnimation(animation) {
  if (!animation) {
    return "";
  }

  return `
    <div class="card-cast-layer">
      <div class="card-cast-flare ${animation.variant}"></div>
      <div class="card-cast-card ${animation.variant}">
        <img
          class="card-cast-image"
          src="${animation.image}"
          alt="${animation.name}"
          onerror="this.onerror=null;this.src='${animation.fallback}';"
        />
        <div class="card-cast-copy">
          <p class="eyebrow">${animation.type}</p>
          <h3>${animation.name}</h3>
        </div>
      </div>
    </div>
  `;
}

function renderEnemy(enemy, selectedEnemyId, index) {
  const selectedClass = enemy.id === selectedEnemyId ? "selected" : "";
  const enemyImage = enemy.art?.enemyImage ?? "./src/assets/enemy-placeholder.svg";
  return `
    <button class="combatant enemy-card ${selectedClass}" data-action="select-enemy" data-id="${enemy.id}" data-combatant="enemy-${index}">
      <div class="combatant-frame enemy-frame">
        <div class="enemy-portrait-wrap">
          <img
            class="portrait"
            src="${enemyImage}"
            alt="${enemy.name}"
            onerror="this.onerror=null;this.src='./src/assets/enemy-placeholder.svg';"
          />
          ${renderIntent(enemy.intent)}
        </div>
        <div class="enemy-nameplate">${enemy.name}</div>
        ${renderCombatFooter(enemy, "enemy")}
      </div>
    </button>
  `;
}

function renderCard(cardId, state, index) {
  const card = CARD_LIBRARY[cardId];
  const disabled = !card || state.player.energy < card.cost || state.outcome;
  const art = resolveCardArt(cardId, card);
  return `
    <button class="card" data-action="play-card" data-id="${index}" ${disabled ? "disabled" : ""}>
      <div class="card-top">
        <div class="card-cost">${card.cost}</div>
        <p class="card-type">${card.type}</p>
      </div>
      <div class="card-art-frame ${art.variant}">
        <img
          class="card-art-image"
          src="${art.src}"
          alt="${art.alt}"
          onerror="this.onerror=null;this.src='${art.fallback}';"
        />
      </div>
      <div>
        <h3>${card.name}</h3>
        <p class="card-description">${card.description}</p>
      </div>
      <p class="card-foot">${hasKeyword(card, "exhaust") ? "Exhausts after play" : card.rarity}</p>
    </button>
  `;
}

function nodeGlyph(type) {
  const glyphs = {
    hallway: "X",
    elite: "E",
    campfire: "R",
    treasure: "$",
    boss: "B",
  };
  return glyphs[type] ?? "?";
}

function renderIntent(intent) {
  const info = describeIntent(intent);
  return `
    <div class="intent-badge">
      <div class="intent-icon" data-tooltip-title="${info.name}" data-tooltip-desc="${info.description}" aria-label="${info.name}">
        <span class="intent-symbol">${info.icon}</span>
        ${info.count ? `<span class="intent-count">${info.count}</span>` : ""}
      </div>
    </div>
  `;
}

function renderCombatFooter(unit, variant) {
  return `
    <div class="combat-footer ${variant}-footer">
      ${renderHpBar(unit.hp, unit.maxHp, variant)}
      ${renderEffects(unit)}
    </div>
  `;
}

function renderHpBar(current, max, variant) {
  const ratio = max > 0 ? Math.max(0, Math.min(100, (current / max) * 100)) : 0;
  return `
    <div class="hp-block">
      <div class="hp-track ${variant}">
        <div class="hp-fill ${variant}" style="width: ${ratio}%"></div>
        <div class="hp-values">${current}/${max}</div>
      </div>
    </div>
  `;
}

function renderEffects(unit) {
  const effects = collectEffects(unit);
  if (effects.length === 0) {
    return `<div class="effects-row empty"><span class="muted">No active effects</span></div>`;
  }

  return `
    <div class="effects-row">
      ${effects
        .map(
          (effect) => `
            <span class="effect-icon" data-tooltip-title="${effect.name}" data-tooltip-desc="${effect.description}">
              ${effect.icon}
              <span class="effect-stack">${effect.value}</span>
            </span>
          `,
        )
        .join("")}
    </div>
  `;
}

function collectEffects(unit) {
  const effectMap = [
    { key: "block", icon: "B", name: "Block", describe: (value) => `Prevents the next ${value} damage taken this turn.` },
    { key: "strength", icon: "S", name: "Strength", describe: (value) => `Adds ${value} damage to attacks.` },
    { key: "weak", icon: "W", name: "Weak", describe: (value) => `Attacks deal reduced damage for ${value} more turns.` },
    { key: "vulnerable", icon: "V", name: "Vulnerable", describe: (value) => `Incoming attacks deal extra damage for ${value} more turns.` },
    { key: "metallicize", icon: "M", name: "Metallicize", describe: (value) => `Gain ${value} block at the start of each turn.` },
  ];

  return effectMap
    .filter((effect) => (unit[effect.key] ?? 0) > 0)
    .map((effect) => ({
      icon: effect.icon,
      name: effect.name,
      description: effect.describe(unit[effect.key]),
      value: unit[effect.key],
    }));
}

function describeIntent(intent) {
  if (!intent) {
    return { icon: "?", name: "Unknown Intent", count: "", description: "The enemy's next action is unclear." };
  }
  if (intent.type === "attack") {
    const repeats = intent.repeats ?? 1;
    return {
      icon: repeats > 1 ? "⚔" : "🗡",
      name: "Attack",
      count: repeats > 1 ? `${intent.value}x${repeats}` : `${intent.value}`,
      description: repeats > 1 ? `Will attack ${repeats} times for ${intent.value} base damage each.` : `Will attack for ${intent.value} base damage.`,
    };
  }
  if (intent.type === "attackBlock") {
    return {
      icon: "🛡",
      name: "Attack and Block",
      count: `${intent.value}`,
      description: `Will attack for ${intent.value} base damage and gain ${intent.block} block.`,
    };
  }
  if (intent.type === "buff") {
    return {
      icon: "▲",
      name: "Buff",
      count: `+${intent.strength ?? intent.block ?? 0}`,
      description: `Will gain ${intent.strength ?? 0} Strength and ${intent.block ?? 0} block.`,
    };
  }
  if (intent.type === "debuff") {
    return {
      icon: "☠",
      name: "Debuff",
      count: `${Math.max(intent.weak ?? 0, intent.vulnerable ?? 0)}`,
      description: `Will apply ${intent.weak ?? 0} Weak and ${intent.vulnerable ?? 0} Vulnerable.`,
    };
  }
  return { icon: "?", name: intent.label, count: "", description: "The enemy is preparing something unusual." };
}

function describeEncounterHeadline(state) {
  if (state.enemies.length === 0) {
    return "No active enemy";
  }
  if (state.enemies.length === 1) {
    return state.enemies[0].name;
  }
  return `${state.enemies.length} Enemies`;
}

function renderNonBattle(state) {
  if (state.outcome === "victory") {
    return `
      <section class="overlay-card">
        <p class="eyebrow">Run complete</p>
        <h2>You toppled the Neurolith</h2>
        <p>The prototype run is complete. Restart to climb again.</p>
        <button class="button-primary" data-action="restart">Start New Run</button>
      </section>
    `;
  }

  return `
    <section class="map-screen">
      <div class="map-panel">
        <div class="map-head">
          <div>
            <p class="eyebrow">Run Map</p>
            <h2>${describeScreen(state)}</h2>
          </div>
          <p class="muted">${describeHint(state)}</p>
        </div>
        <div class="map-grid main-map-grid">
          ${state.mapNodes.map((node) => renderNode(node, state)).join("")}
        </div>
      </div>
      <div class="route-info-grid">
        <div class="control-card">
          <p class="eyebrow">Adventurer</p>
          <h3>${state.player.name}</h3>
          <p>HP ${state.player.hp}/${state.player.maxHp}</p>
          <p>Energy ${state.player.maxEnergy}</p>
          <p>Deck ${state.player.deck.length} cards</p>
          <p>Relics ${state.player.relics.length}</p>
        </div>
        <div class="control-card">
          <p class="eyebrow">Relics</p>
          ${
            state.player.relics.length === 0
              ? `<p class="muted">No relics yet.</p>`
              : state.player.relics
                  .map((relicId) => {
                    const relic = describeRelic(relicId);
                    return `<p>${relic.icon} ${relic.name}</p>`;
                  })
                  .join("")
          }
        </div>
        <div class="control-card art-preview-card">
          <p class="eyebrow">${state.loadout.title}</p>
          <h3>${state.loadout.enemyName}</h3>
          <div class="art-preview-grid">
            <img
              class="art-preview-image"
              src="${state.loadout.enemyImage}"
              alt="${state.loadout.enemyName}"
              onerror="this.onerror=null;this.src='./src/assets/enemy-placeholder.svg';"
            />
            <img
              class="art-preview-image"
              src="${state.loadout.weaponImage}"
              alt="${state.loadout.weaponName}"
              onerror="this.onerror=null;this.src='./src/assets/player-placeholder.svg';"
            />
          </div>
          <p>${state.loadout.enemyDescription}</p>
          <p class="muted">Weapon: ${state.loadout.weaponName}</p>
        </div>
        <div class="control-card">
          <p class="eyebrow">Recent Log</p>
          <div class="log-list">
            ${state.log.slice(0, 8).map((entry) => `<p class="log-entry">${entry}</p>`).join("")}
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderDeckStrip(state) {
  return `
    <section class="deck-strip">
      <div class="stat-card">
        <p class="eyebrow">Draw</p>
        <h3>${state.player.drawPile.length}</h3>
      </div>
      <div class="stat-card">
        <p class="eyebrow">Discard</p>
        <h3>${state.player.discardPile.length}</h3>
      </div>
      <div class="stat-card">
        <p class="eyebrow">Exhaust</p>
        <h3>${state.player.exhaustPile.length}</h3>
      </div>
    </section>
  `;
}

function renderOverlay(state) {
  if (state.rewardOptions.length > 0 && state.screen !== "battle" && !state.outcome) {
    return `
      <div class="overlay">
        <div class="overlay-card">
          <p class="eyebrow">Reward</p>
          <h2>Choose a card</h2>
          <div class="reward-options">
            ${state.rewardOptions.map((cardId) => renderRewardCard(cardId)).join("")}
          </div>
          <button class="button-muted" data-action="skip-reward">Skip reward</button>
        </div>
      </div>
    `;
  }

  if (state.screen === "campfire") {
    return `
      <div class="overlay">
        <div class="overlay-card">
          <p class="eyebrow">Campfire</p>
          <h2>Rest or move on</h2>
          <p>You may recover 16 HP before continuing.</p>
          <button class="button-primary" data-action="rest">Rest</button>
        </div>
      </div>
    `;
  }

  if (state.screen === "treasure") {
    const relic = state.pendingRelicRewardId ? RELIC_LIBRARY[state.pendingRelicRewardId] : null;
    return `
      <div class="overlay">
        <div class="overlay-card">
          <p class="eyebrow">Treasure</p>
          <h2>${relic?.name ?? "Relic"}</h2>
          <p>${relic?.description ?? "A strange treasure hums in the dark."}</p>
          <button class="button-primary" data-action="take-relic">Take relic</button>
        </div>
      </div>
    `;
  }

  if (state.outcome === "defeat") {
    return `
      <div class="overlay">
        <div class="overlay-card">
          <p class="eyebrow">Defeat</p>
          <h2>The climb ends here</h2>
          <p>Your deck was not enough this time.</p>
          <button class="button-primary" data-action="restart">Try another run</button>
        </div>
      </div>
    `;
  }

  return "";
}

function renderRewardCard(cardId) {
  const card = CARD_LIBRARY[cardId];
  const art = resolveCardArt(cardId, card);
  return `
    <button class="reward-option" data-action="claim-reward" data-id="${cardId}">
      <p class="eyebrow">${card.type}</p>
      <div class="card-art-frame ${art.variant}">
        <img
          class="card-art-image"
          src="${art.src}"
          alt="${art.alt}"
          onerror="this.onerror=null;this.src='${art.fallback}';"
        />
      </div>
      <h3>${card.name}</h3>
      <p>${card.description}</p>
      <p class="muted">Cost ${card.cost}</p>
    </button>
  `;
}

function resolveCardArt(cardId, card) {
  const cardArt = getCardArt(cardId);
  return {
    src: cardArt.image,
    alt: cardArt.title,
    fallback: cardArt.fallback,
    variant: card.type === "Attack" ? "card-art-weapon" : "card-art-enemy",
  };
}

function describeScreen(state) {
  if (state.outcome === "defeat") {
    return "Run failed";
  }
  const nextNode = state.mapNodes.find((node) => node.available && !node.completed);
  return nextNode ? `Next stop: ${nextNode.label}` : "The path is clear";
}

function describeHint(state) {
  const nextNode = state.mapNodes.find((node) => node.available && !node.completed);
  if (!nextNode) {
    return "The prototype run is complete.";
  }
  if (nextNode.type === "boss") {
    return "One final battle waits at the top.";
  }
  return "Pick the highlighted node to continue climbing.";
}

function travelToNode(state, id) {
  const node = state.mapNodes.find((entry) => entry.id === id);
  if (!node || !node.available || node.completed) {
    return;
  }

  state.loadout = getLevelArt(node.id);
  state.floor = node.index + 1;
  addLog(state, `You enter ${node.label}.`);

  if (node.type === "hallway" || node.type === "elite" || node.type === "boss") {
    startBattle(state, node);
    return;
  }
  if (node.type === "campfire") {
    state.screen = "campfire";
    return;
  }
  if (node.type === "treasure") {
    state.pendingRelicRewardId = pickRelicReward(state);
    state.screen = "treasure";
  }
}

function startBattle(state, node) {
  const type = node.type;
  const template = clonePick(ENCOUNTERS[type]);
  const enemyTemplates = template.enemies ?? [template];
  const art = getLevelArt(node.id);
  state.enemies = enemyTemplates.map((enemyTemplate, index) => ({
    ...enemyTemplate,
    id: `enemy-${index}-${enemyTemplate.name.toLowerCase().replaceAll(" ", "-")}`,
    hp: enemyTemplate.maxHp,
    block: 0,
    strength: 0,
    weak: 0,
    vulnerable: 0,
    intentIndex: 0,
    intent: enemyTemplate.intents[0],
    art,
  }));
  state.selectedEnemyId = state.enemies[0]?.id ?? null;

  state.player.block = 0;
  state.player.energy = state.player.maxEnergy;
  state.player.drawPile = shuffle([...state.player.deck]);
  state.player.discardPile = [];
  state.player.hand = [];
  state.player.exhaustPile = [];
  state.player.weak = 0;
  state.player.vulnerable = 0;
  state.screen = "battle";
  state.battle = { type: node.type, nodeId: node.id };
  state.loadout = art;
  triggerRelicEvent(state, "onBattleStart", battleContext(state));
  drawCards(state, 5);
  addLog(state, `${describeEncounterHeadline(state)} appear.`);
}

// [FX] [SFX] playCard now returns { fx, sfx } so the caller (handleAction) can
// fire them after re-render — no change to the public call signature.
function playCard(state, index) {
  if (state.screen !== "battle" || state.outcome) {
    return null; // [FX]
  }
  const cardId = state.player.hand[index];
  const card = CARD_LIBRARY[cardId];
  if (!card || card.cost > state.player.energy) {
    return null; // [FX]
  }

  state.player.energy -= card.cost;
  state.player.hand.splice(index, 1);
  const feedback = buildCardFeedback(card, state);
  triggerCardEvent(state, card, "onPlay", battleContext(state, card));
  triggerRelicEvent(state, "onCardPlayed", battleContext(state, card));
  state.cardAnimation = createCardAnimation(cardId, card);

  if (hasKeyword(card, "exhaust")) {
    state.player.exhaustPile.push(cardId);
  } else {
    state.player.discardPile.push(cardId);
  }

  processDefeatedEnemies(state);
  if (state.enemies.length === 0) {
    winBattle(state);
    // [SFX] victory sound queued by caller via sfx list
    return { fx: feedback.fx, sfx: [...feedback.sfx, "victory"] };
  }

  return feedback; // [FX] [SFX]
}

function selectEnemyTarget(state, enemyId) {
  if (state.screen !== "battle") {
    return;
  }

  const enemy = state.enemies.find((entry) => entry.id === enemyId && entry.hp > 0);
  if (!enemy) {
    return;
  }

  state.selectedEnemyId = enemy.id;
}

function createCardAnimation(cardId, card) {
  const art = resolveCardArt(cardId, card);
  return {
    id: `${cardId}-${Date.now()}`,
    image: art.src,
    fallback: art.fallback,
    name: card.name,
    type: card.type,
    variant: card.type === "Attack" ? "attack-cast" : "skill-cast",
  };
}

function endTurn(state) {
  if (state.screen !== "battle" || state.outcome) {
    return null;
  }

  triggerRelicEvent(state, "onTurnEnd", battleContext(state));
  state.player.discardPile.push(...state.player.hand);
  state.player.hand = [];
  const intentResult = runEnemyIntent(state);
  if (state.outcome === "defeat") {
    triggerRelicEvent(state, "onBattleEnd", { ...battleContext(state), result: "defeat" });
    return { fx: intentResult?.fx ?? [], sfx: [...(intentResult?.sfx ?? []), "defeat"] };
  }

  state.player.block = state.player.metallicize;
  state.player.energy = state.player.maxEnergy;
  triggerRelicEvent(state, "onTurnStart", battleContext(state));
  tickDownStatus(state.player);
  for (const enemy of state.enemies) {
    tickDownStatus(enemy);
    advanceEnemyIntent(enemy);
  }
  drawCards(state, 5);
  for (const enemy of state.enemies) {
    addLog(state, `${enemy.name} prepares ${enemy.intent.label}.`);
  }

  return intentResult ?? { fx: [], sfx: [] }; // [FX]
}

// [FX] runEnemyIntent now returns { fx, sfx } instead of void.
function runEnemyIntent(state) {
  const fxEvents = [];
  const sfxList = [];

  for (const enemy of state.enemies) {
    const intent = enemy.intent;
    if (!intent) {
      continue;
    }

    if (intent.type === "attack" || intent.type === "attackBlock") {
      const repeats = intent.repeats ?? 1;
      for (let index = 0; index < repeats; index += 1) {
        const damage = adjustedDamage(intent.value + enemy.strength, enemy.weak, state.player.vulnerable);
        absorbDamage(state.player, damage);
        addLog(state, `${enemy.name} hits for ${damage}.`);
        fxEvents.push({ type: "damage", target: "player:0", value: damage });
        sfxList.push("enemyAttack");
        if (state.player.hp <= 0) {
          state.outcome = "defeat";
          state.screen = "map";
        return { fx: fxEvents, sfx: sfxList }; // [FX]
        }
      }
    }

    if (intent.type === "attackBlock" && intent.block) {
      enemy.block += intent.block;
      fxEvents.push({ type: "block", target: getEnemyFxTarget(state, enemy.id), value: intent.block });
      sfxList.push("block");
    }
    if (intent.type === "buff") {
      enemy.strength += intent.strength ?? 0;
      enemy.block += intent.block ?? 0;
      addLog(state, `${enemy.name} grows stronger.`);
      fxEvents.push({ type: "buff", target: getEnemyFxTarget(state, enemy.id), label: intent.label });
      sfxList.push("buff");
    }
    if (intent.type === "debuff") {
      state.player.weak += intent.weak ?? 0;
      state.player.vulnerable += intent.vulnerable ?? 0;
      addLog(state, `${enemy.name} curses your footing.`);
      fxEvents.push({ type: "debuff", target: "player:0", label: intent.label });
      sfxList.push("debuff");
    }
  }

  return { fx: fxEvents, sfx: sfxList }; // [FX]
}

function winBattle(state) {
  addLog(state, "The encounter is cleared.");
  state.enemies = [];
  state.selectedEnemyId = null;
  state.player.block = 0;
  state.player.energy = state.player.maxEnergy;
  state.rewardOptions = pickRewardCards(state.player.deck);
  state.screen = "map";
  state.mapNodes[state.floor - 1].completed = true;
  unlockNextNode(state);
  triggerRelicEvent(state, "onBattleEnd", { ...battleContext(state), result: "victory" });

  if (state.battle?.type === "boss") {
    state.outcome = "victory";
    state.screen = "map";
  }
}

function claimReward(state, cardId) {
  state.player.deck.push(cardId);
  addLog(state, `You add ${CARD_LIBRARY[cardId].name} to your deck.`);
  state.rewardOptions = [];
  state.screen = "map";
}

function unlockNextNode(state) {
  const next = state.mapNodes[state.floor];
  if (next) {
    next.available = true;
  }
}

function completeCurrentNode(state) {
  const node = state.mapNodes[state.floor - 1];
  if (!node) {
    return;
  }
  node.completed = true;
  unlockNextNode(state);
}

function buildCardFeedback(card, state) {
  const feedback = {
    fx: [],
    sfx: ["cardPlay"],
  };

  for (const behavior of card.behaviors ?? []) {
    if (behavior.trigger !== "onPlay") {
      continue;
    }

    collectEffectFeedback(behavior.effects ?? [], state, feedback);
  }

  feedback.sfx = [...new Set(feedback.sfx)];
  return feedback;
}

function collectEffectFeedback(effects, state, feedback) {
  for (const effect of effects) {
    if (!effect?.type) {
      continue;
    }

    if (effect.type === "repeat") {
      collectEffectFeedback(effect.effects ?? [], state, feedback);
      continue;
    }

    if (effect.type === "condition") {
      collectEffectFeedback(effect.effects ?? [], state, feedback);
      collectEffectFeedback(effect.elseEffects ?? [], state, feedback);
      continue;
    }

    if (effect.type === "damage") {
      const targets = getFxTargetsForEffect(state, effect.target);
      for (const target of targets) {
        feedback.fx.push({ type: "damage", target, value: resolveFxValue(state, effect) });
      }
      feedback.sfx.push("attack");
      continue;
    }

    if (effect.type === "heal") {
      const targets = getFxTargetsForEffect(state, effect.target);
      for (const target of targets) {
        feedback.fx.push({ type: "heal", target, value: resolveFxValue(state, effect) });
      }
      feedback.sfx.push("heal");
      continue;
    }

    if (effect.type === "modifyStat") {
      const targets = getFxTargetsForEffect(state, effect.target);
      const isDebuff = effect.stat === "weak" || effect.stat === "vulnerable";
      const fxType = effect.stat === "block" ? "block" : isDebuff ? "debuff" : "buff";
      for (const target of targets) {
        feedback.fx.push({
          type: fxType,
          target,
          value: fxType === "block" ? resolveFxValue(state, effect) : undefined,
          label: fxType === "block" ? undefined : formatStatLabel(effect.stat, resolveFxValue(state, effect)),
        });
      }
      feedback.sfx.push(fxType === "block" ? "block" : isDebuff ? "debuff" : "buff");
      continue;
    }

    if (effect.type === "gainEnergy") {
      feedback.sfx.push("buff");
      continue;
    }

    if (effect.type === "drawCards") {
      feedback.sfx.push("cardPlay");
    }
  }
}

function getFxTargetsForEffect(state, target) {
  if (target === "self" || target === "owner" || target === "player") {
    return ["player:0"];
  }

  if (target === "allEnemies") {
    return state.enemies.map((enemy) => getEnemyFxTarget(state, enemy.id));
  }

  return [getEnemyFxTarget(state, state.selectedEnemyId)];
}

function getEnemyFxTarget(state, enemyId) {
  const index = state.enemies.findIndex((enemy) => enemy.id === enemyId);
  const fallbackIndex = state.enemies.findIndex((enemy) => enemy.hp > 0);
  const resolvedIndex = index >= 0 ? index : Math.max(0, fallbackIndex);
  return `enemy:${resolvedIndex}`;
}

function resolveFxValue(state, effect) {
  if (typeof effect.amount === "number") {
    if (effect.type === "damage" && effect.useCombatModifiers) {
      const targetId = effect.target === "allEnemies" ? state.enemies[0]?.id : state.selectedEnemyId;
      const target = state.enemies.find((enemy) => enemy.id === targetId) ?? state.enemies[0];
      return adjustedDamage(
        effect.amount + state.player.strength,
        state.player.weak,
        target?.vulnerable ?? 0,
      );
    }
    return effect.amount;
  }
  if (effect.amount === "playerStrength") {
    return state.player.strength;
  }
  if (effect.amount === "cardsInHand") {
    return state.player.hand.length;
  }
  return 0;
}

function formatStatLabel(stat, amount) {
  const readable = stat.replaceAll("_", " ");
  return `${amount >= 0 ? "+" : ""}${amount} ${readable}`;
}

function adjustedDamage(amount, weak, targetVulnerable) {
  let total = amount;
  if (weak > 0) {
    total = Math.floor(total * 0.75);
  }
  if (targetVulnerable > 0) {
    total = Math.floor(total * 1.5);
  }
  return Math.max(0, total);
}

function absorbDamage(target, damage) {
  const blocked = Math.min(target.block, damage);
  target.block -= blocked;
  target.hp -= damage - blocked;
}

function processDefeatedEnemies(state) {
  const defeated = state.enemies.filter((enemy) => enemy.hp <= 0);
  for (const enemy of defeated) {
    addLog(state, `${enemy.name} falls.`);
  }
  state.enemies = state.enemies.filter((enemy) => enemy.hp > 0);
  if (!state.enemies.some((enemy) => enemy.id === state.selectedEnemyId)) {
    state.selectedEnemyId = state.enemies[0]?.id ?? null;
  }
}

function tickDownStatus(unit) {
  unit.weak = Math.max(0, unit.weak - 1);
  unit.vulnerable = Math.max(0, unit.vulnerable - 1);
}

function advanceEnemyIntent(enemy) {
  enemy.intentIndex = (enemy.intentIndex + 1) % enemy.intents.length;
  enemy.intent = enemy.intents[enemy.intentIndex];
}

function drawCards(state, amount) {
  for (let index = 0; index < amount; index += 1) {
    if (state.player.drawPile.length === 0) {
      if (state.player.discardPile.length === 0) {
        return;
      }
      state.player.drawPile = shuffle([...state.player.discardPile]);
      state.player.discardPile = [];
    }

    const nextCardId = state.player.drawPile.pop();
    if (!nextCardId) {
      continue;
    }

    const card = CARD_LIBRARY[nextCardId];
    state.player.hand.push(nextCardId);
    triggerCardEvent(state, card, "onDraw", battleContext(state, card));
    triggerRelicEvent(state, "onCardDrawn", battleContext(state, card));
  }
}

function pickRewardCards(deck) {
  const pool = CARD_REWARD_POOL.filter((cardId) => !deck.includes(cardId) || deck.length > 9);
  return shuffle(pool).slice(0, 3);
}

function pickRelicReward(state) {
  const available = TREASURE_RELIC_POOL.filter((relicId) => !state.player.relics.includes(relicId));
  return shuffle(available.length > 0 ? available : TREASURE_RELIC_POOL)[0];
}

function grantRelic(state, relicId) {
  const relic = RELIC_LIBRARY[relicId];
  if (!relic) {
    return;
  }
  if (!state.player.relics.includes(relicId)) {
    state.player.relics.push(relicId);
  }
  addLog(state, `You claim ${relic.name}.`);
}

function battleContext(state, card = null) {
  return {
    state,
    card,
    targetEnemyId: state.selectedEnemyId,
    absorbDamage,
    drawCards,
  };
}

function addLog(state, message) {
  state.log.unshift(message);
}

function shuffle(items) {
  const array = [...items];
  for (let index = array.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1));
    [array[index], array[swapIndex]] = [array[swapIndex], array[index]];
  }
  return array;
}

function clonePick(list) {
  return structuredClone(list[Math.floor(Math.random() * list.length)]);
}
