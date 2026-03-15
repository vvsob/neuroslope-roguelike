import { getCardArt } from "./cardArt.js";
import { getLevelArt } from "./levelArt.js";

const STARTING_DECK = [
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
];

const CARD_LIBRARY = {
  strike: {
    id: "strike",
    name: "Strike",
    cost: 1,
    type: "Attack",
    description: "Deal 6 damage.",
    play(state) {
      dealDamage(state, 6);
      return "You slash for 6.";
    },
  },
  defend: {
    id: "defend",
    name: "Defend",
    cost: 1,
    type: "Skill",
    description: "Gain 5 block.",
    play(state) {
      state.player.block += 5;
      return "You brace for 5 block.";
    },
  },
  bash: {
    id: "bash",
    name: "Bash",
    cost: 2,
    type: "Attack",
    description: "Deal 8 damage. Apply 2 Vulnerable.",
    play(state) {
      dealDamage(state, 8);
      state.enemy.vulnerable += 2;
      return "You bash for 8 and apply Vulnerable.";
    },
  },
  focus: {
    id: "focus",
    name: "Focus",
    cost: 1,
    type: "Skill",
    description: "Gain 2 Strength this combat.",
    play(state) {
      state.player.strength += 2;
      return "Your stance sharpens. Gain 2 Strength.";
    },
  },
  quick_slash: {
    id: "quick_slash",
    name: "Quick Slash",
    cost: 1,
    type: "Attack",
    description: "Deal 7 damage. Draw 1 card.",
    play(state) {
      dealDamage(state, 7);
      drawCards(state, 1);
      return "Quick Slash hits for 7 and cycles your hand.";
    },
  },
  iron_shell: {
    id: "iron_shell",
    name: "Iron Shell",
    cost: 1,
    type: "Skill",
    description: "Gain 7 block. Gain 1 block next turn.",
    play(state) {
      state.player.block += 7;
      state.player.metallicize += 1;
      return "Iron Shell grants 7 block and lasting plating.";
    },
  },
  cleave: {
    id: "cleave",
    name: "Cleave",
    cost: 1,
    type: "Attack",
    description: "Deal 9 damage.",
    play(state) {
      dealDamage(state, 9);
      return "Cleave tears through the enemy for 9.";
    },
  },
  second_wind: {
    id: "second_wind",
    name: "Second Wind",
    cost: 1,
    type: "Skill",
    description: "Heal 4 HP. Exhaust.",
    exhaust: true,
    play(state) {
      state.player.hp = Math.min(state.player.maxHp, state.player.hp + 4);
      return "You recover 4 HP.";
    },
  },
};

const ENCOUNTERS = {
  hallway: [
    {
      name: "Ash Ghoul",
      maxHp: 42,
      intents: [
        { type: "attack", value: 8, label: "Claw 8" },
        { type: "buff", strength: 2, label: "Rage +2 Strength" },
        { type: "attackBlock", value: 6, block: 6, label: "Rake 6 + Block 6" },
      ],
    },
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
  elite: [
    {
      name: "Bronze Husk",
      maxHp: 68,
      intents: [
        { type: "attackBlock", value: 10, block: 8, label: "Crush 10 + Block 8" },
        { type: "buff", strength: 3, label: "Harden +3 Strength" },
        { type: "attack", value: 14, label: "Hammerfall 14" },
      ],
    },
  ],
  boss: [
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
      setState((draft) => playCard(draft, id));
      scheduleCardAnimationCleanup();
      return;
    }

    if (action === "end-turn") {
      setState((draft) => endTurn(draft));
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
      return;
    }

    if (action === "take-relic") {
      setState((draft) => {
        draft.player.maxEnergy += 1;
        draft.player.energy = draft.player.maxEnergy;
        addLog(draft, "You claim a humming core. Max energy increases by 1.");
        completeCurrentNode(draft);
        draft.screen = "map";
      });
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
    },
    enemy: null,
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
        <p class="muted">Energy ${state.player.energy}/${state.player.maxEnergy} | Strength ${state.player.strength}</p>
      </div>
      <div class="top-pill">
        <p class="eyebrow">Encounter</p>
        <h3>${state.enemy ? state.enemy.name : "No active enemy"}</h3>
        <p class="muted">${state.enemy ? "Battle in progress" : "Choose the next room on the map."}</p>
      </div>
    </section>
  `;
}

function renderBattle(state) {
  const enemyImage = state.enemy?.art?.enemyImage ?? "./src/assets/enemy-placeholder.svg";
  const weaponImage = state.loadout?.weaponImage ?? "./src/assets/player-placeholder.svg";
  return `
    <section class="spire-battle-layout">
      <section class="battle-scene">
        ${renderCardAnimation(state.cardAnimation)}
        <div class="enemy-side combatant">
          <div class="combatant-frame enemy-frame">
            <img
              class="portrait"
              src="${enemyImage}"
              alt="${state.enemy.name}"
              onerror="this.onerror=null;this.src='./src/assets/enemy-placeholder.svg';"
            />
            ${renderIntent(state.enemy.intent)}
            ${renderCombatFooter(state.enemy, "enemy")}
          </div>
        </div>
        <div class="player-side combatant">
          <div class="combatant-frame player-frame">
            <div class="player-loadout">
              <img class="portrait" src="./src/assets/player-placeholder.svg" alt="${state.player.name}" />
              ${renderWeaponPanel(state.loadout, weaponImage)}
              ${renderCombatFooter(state.player, "player")}
            </div>
          </div>
        </div>
      </section>
      <section class="battle-hud">
        <div class="battle-sidepanel control-card">
          <p class="eyebrow">Turn</p>
          <h3>Energy ${state.player.energy}/${state.player.maxEnergy}</h3>
          <p class="muted">Hand ${state.player.hand.length} | Draw ${state.player.drawPile.length}</p>
          <p class="muted">Discard ${state.player.discardPile.length} | Exhaust ${state.player.exhaustPile.length}</p>
          <button class="button-primary end-turn-button" data-action="end-turn">End Turn</button>
        </div>
        <div class="hand-panel">
          <div class="hand-backdrop"></div>
          <div class="hand-shell">
            <div class="hand-head">
              <div>
                <p class="eyebrow">Hand</p>
                <h3>Choose a card</h3>
              </div>
              <p class="muted">Play cards, then end turn.</p>
            </div>
            <div class="hand-row">
              ${state.player.hand.map((cardId, index) => renderCard(cardId, state, index)).join("")}
            </div>
          </div>
        </div>
        <div class="battle-deckbar">
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

function renderWeaponPanel(loadout, weaponImage) {
  return `
    <div class="weapon-panel">
      <div class="weapon-art-frame">
        <img
          class="weapon-art"
          src="${weaponImage}"
          alt="${loadout.weaponName}"
          onerror="this.onerror=null;this.src='./src/assets/player-placeholder.svg';"
        />
      </div>
      <div class="weapon-copy">
        <p class="eyebrow">${loadout.title} Weapon</p>
        <h3>${loadout.weaponName}</h3>
        <p class="muted">${loadout.weaponDescription}</p>
      </div>
    </div>
  `;
}

function renderCard(cardId, state, index) {
  const card = CARD_LIBRARY[cardId];
  const disabled = state.player.energy < card.cost || state.outcome;
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
      <p class="card-foot">${card.exhaust ? "Exhausts after play" : "Returns to discard pile"}</p>
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
    <div
      class="intent-icon"
      data-tooltip-title="${info.name}"
      data-tooltip-desc="${info.description}"
      aria-label="${info.name}"
    >
      ${info.icon}
      <span class="intent-count">${info.count}</span>
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
            <span
              class="effect-icon"
              data-tooltip-title="${effect.name}"
              data-tooltip-desc="${effect.description}"
            >
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
    {
      key: "block",
      icon: "B",
      name: "Block",
      describe: (value) => `Prevents the next ${value} damage taken this turn.`,
    },
    {
      key: "strength",
      icon: "S",
      name: "Strength",
      describe: (value) => `Adds ${value} damage to attack cards and enemy attacks.`,
    },
    {
      key: "weak",
      icon: "W",
      name: "Weak",
      describe: (value) => `Attacks deal reduced damage for ${value} more turns.`,
    },
    {
      key: "vulnerable",
      icon: "V",
      name: "Vulnerable",
      describe: (value) => `Incoming attacks deal extra damage for ${value} more turns.`,
    },
    {
      key: "metallicize",
      icon: "M",
      name: "Metallicize",
      describe: (value) => `Gain ${value} block at the start of each turn.`,
    },
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
    return { icon: "?", name: "Unknown Intent", description: "The enemy's next action is unclear." };
  }

  if (intent.type === "attack") {
    const repeats = intent.repeats ?? 1;
    return {
      icon: repeats > 1 ? "⚔" : "🗡",
      name: "Attack",
      count: repeats > 1 ? `${intent.value}x${repeats}` : `${intent.value}`,
      description:
        repeats > 1
          ? `Will attack ${repeats} times for ${intent.value} base damage each.`
          : `Will attack for ${intent.value} base damage.`,
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

  return {
    icon: "?",
    name: intent.label,
    count: "",
    description: "The enemy is preparing something unusual.",
  };
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
    return `
      <div class="overlay">
        <div class="overlay-card">
          <p class="eyebrow">Treasure</p>
          <h2>Humming Core</h2>
          <p>Gain 1 max energy for the rest of the run.</p>
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
    state.screen = "treasure";
    return;
  }
}

function startBattle(state, node) {
  const template = clonePick(ENCOUNTERS[node.type]);
  const art = getLevelArt(node.id);
  state.enemy = {
    ...template,
    hp: template.maxHp,
    block: 0,
    strength: 0,
    weak: 0,
    vulnerable: 0,
    intentIndex: 0,
    intent: template.intents[0],
    art,
  };

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
  drawCards(state, 5);
  addLog(state, `${state.enemy.name} appears with intent: ${state.enemy.intent.label}.`);
}

function playCard(state, index) {
  if (state.screen !== "battle" || state.outcome) {
    return;
  }

  const cardId = state.player.hand[index];
  const card = CARD_LIBRARY[cardId];
  if (!card || card.cost > state.player.energy) {
    return;
  }

  state.player.energy -= card.cost;
  state.player.hand.splice(index, 1);
  state.cardAnimation = createCardAnimation(cardId, card);
  const message = card.play(state);

  if (card.exhaust) {
    state.player.exhaustPile.push(cardId);
  } else {
    state.player.discardPile.push(cardId);
  }

  addLog(state, message);

  if (state.enemy.hp <= 0) {
    winBattle(state);
  }
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
    return;
  }

  state.player.discardPile.push(...state.player.hand);
  state.player.hand = [];
  runEnemyIntent(state);

  if (state.outcome === "defeat") {
    return;
  }

  state.player.block = state.player.metallicize;
  state.player.energy = state.player.maxEnergy;
  tickDownStatus(state.player);
  tickDownStatus(state.enemy);
  advanceEnemyIntent(state.enemy);
  drawCards(state, 5);
  addLog(state, `${state.enemy.name} prepares ${state.enemy.intent.label}.`);
}

function runEnemyIntent(state) {
  const intent = state.enemy.intent;
  if (!intent) {
    return;
  }

  if (intent.type === "attack" || intent.type === "attackBlock") {
    const repeats = intent.repeats ?? 1;
    for (let i = 0; i < repeats; i += 1) {
      const damage = adjustedDamage(intent.value + state.enemy.strength, state.enemy.weak, state.player.vulnerable);
      absorbDamage(state.player, damage);
      addLog(state, `${state.enemy.name} hits for ${damage}.`);
      if (state.player.hp <= 0) {
        state.outcome = "defeat";
        state.screen = "map";
        return;
      }
    }
  }

  if (intent.type === "attackBlock" && intent.block) {
    state.enemy.block += intent.block;
  }

  if (intent.type === "buff") {
    state.enemy.strength += intent.strength ?? 0;
    state.enemy.block += intent.block ?? 0;
    addLog(state, `${state.enemy.name} grows stronger.`);
  }

  if (intent.type === "debuff") {
    state.player.weak += intent.weak ?? 0;
    state.player.vulnerable += intent.vulnerable ?? 0;
    addLog(state, `${state.enemy.name} curses your footing.`);
  }
}

function winBattle(state) {
  addLog(state, `${state.enemy.name} falls.`);
  state.enemy = null;
  state.player.block = 0;
  state.player.energy = state.player.maxEnergy;
  state.rewardOptions = pickRewardCards(state.player.deck);
  state.screen = "map";
  state.mapNodes[state.floor - 1].completed = true;
  unlockNextNode(state);

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

function dealDamage(state, baseAmount) {
  const damage = adjustedDamage(
    baseAmount + state.player.strength,
    state.player.weak,
    state.enemy.vulnerable,
  );
  absorbDamage(state.enemy, damage);
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

function tickDownStatus(unit) {
  unit.weak = Math.max(0, unit.weak - 1);
  unit.vulnerable = Math.max(0, unit.vulnerable - 1);
}

function advanceEnemyIntent(enemy) {
  enemy.intentIndex = (enemy.intentIndex + 1) % enemy.intents.length;
  enemy.intent = enemy.intents[enemy.intentIndex];
}

function drawCards(state, amount) {
  for (let i = 0; i < amount; i += 1) {
    if (state.player.drawPile.length === 0) {
      if (state.player.discardPile.length === 0) {
        return;
      }
      state.player.drawPile = shuffle([...state.player.discardPile]);
      state.player.discardPile = [];
    }

    const nextCard = state.player.drawPile.pop();
    if (nextCard) {
      state.player.hand.push(nextCard);
    }
  }
}

function pickRewardCards(deck) {
  const pool = Object.keys(CARD_LIBRARY).filter((cardId) => !STARTING_DECK.includes(cardId) || deck.length > 9);
  return shuffle(pool).slice(0, 3);
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
