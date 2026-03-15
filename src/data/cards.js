export const STARTING_DECK = [
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

export const CARD_LIBRARY = {
  strike: {
    id: "strike",
    name: "Strike",
    cost: 1,
    type: "Attack",
    rarity: "Starter",
    description: "Deal 6 damage.",
    behaviors: [
      {
        trigger: "onPlay",
        effects: [
          { type: "damage", target: "opponent", amount: 6, useCombatModifiers: true },
          { type: "log", text: "{playerName} slashes for 6." },
        ],
      },
    ],
  },
  defend: {
    id: "defend",
    name: "Defend",
    cost: 1,
    type: "Skill",
    rarity: "Starter",
    description: "Gain 5 block.",
    behaviors: [
      {
        trigger: "onPlay",
        effects: [
          { type: "modifyStat", target: "self", stat: "block", amount: 5 },
          { type: "log", text: "{playerName} braces for 5 block." },
        ],
      },
    ],
  },
  bash: {
    id: "bash",
    name: "Bash",
    cost: 2,
    type: "Attack",
    rarity: "Starter",
    description: "Deal 8 damage. Apply 2 Vulnerable.",
    behaviors: [
      {
        trigger: "onPlay",
        effects: [
          { type: "damage", target: "opponent", amount: 8, useCombatModifiers: true },
          { type: "modifyStat", target: "opponent", stat: "vulnerable", amount: 2 },
          { type: "log", text: "{playerName} bashes for 8 and applies Vulnerable." },
        ],
      },
    ],
  },
  focus: {
    id: "focus",
    name: "Focus",
    cost: 1,
    type: "Skill",
    rarity: "Starter",
    description: "Gain 2 Strength this combat.",
    behaviors: [
      {
        trigger: "onPlay",
        effects: [
          { type: "modifyStat", target: "self", stat: "strength", amount: 2 },
          { type: "log", text: "{playerName}'s stance sharpens. Gain 2 Strength." },
        ],
      },
    ],
  },
  quick_slash: {
    id: "quick_slash",
    name: "Quick Slash",
    cost: 1,
    type: "Attack",
    rarity: "Common",
    description: "Deal 7 damage. Draw 1 card.",
    behaviors: [
      {
        trigger: "onPlay",
        effects: [
          { type: "damage", target: "opponent", amount: 7, useCombatModifiers: true },
          { type: "drawCards", amount: 1 },
          { type: "log", text: "{playerName} lands Quick Slash and draws 1 card." },
        ],
      },
    ],
  },
  iron_shell: {
    id: "iron_shell",
    name: "Iron Shell",
    cost: 1,
    type: "Skill",
    rarity: "Common",
    description: "Gain 7 block. Gain 1 Metallicize.",
    behaviors: [
      {
        trigger: "onPlay",
        effects: [
          { type: "modifyStat", target: "self", stat: "block", amount: 7 },
          { type: "modifyStat", target: "self", stat: "metallicize", amount: 1 },
          { type: "log", text: "{playerName} fortifies with Iron Shell." },
        ],
      },
    ],
  },
  cleave: {
    id: "cleave",
    name: "Cleave",
    cost: 1,
    type: "Attack",
    rarity: "Common",
    description: "Deal 9 damage to all enemies.",
    behaviors: [
      {
        trigger: "onPlay",
        effects: [
          { type: "damage", target: "allEnemies", amount: 9, useCombatModifiers: true },
          { type: "log", text: "{playerName} tears through the enemy line for 9." },
        ],
      },
    ],
  },
  second_wind: {
    id: "second_wind",
    name: "Second Wind",
    cost: 1,
    type: "Skill",
    rarity: "Common",
    description: "Heal 4 HP. Exhaust.",
    keywords: ["exhaust"],
    behaviors: [
      {
        trigger: "onPlay",
        effects: [
          { type: "heal", target: "self", amount: 4 },
          { type: "log", text: "{playerName} recovers 4 HP." },
        ],
      },
    ],
  },
  ember_script: {
    id: "ember_script",
    name: "Ember Script",
    cost: 1,
    type: "Skill",
    rarity: "Uncommon",
    description: "When drawn, gain 1 Energy. Exhaust.",
    keywords: ["exhaust"],
    behaviors: [
      {
        trigger: "onDraw",
        effects: [
          { type: "gainEnergy", amount: 1 },
          { type: "log", text: "Ember Script surges as it enters your hand. Gain 1 Energy." },
        ],
      },
    ],
  },
  mirrored_edge: {
    id: "mirrored_edge",
    name: "Mirrored Edge",
    cost: 1,
    type: "Attack",
    rarity: "Uncommon",
    description: "Deal 5 damage twice.",
    behaviors: [
      {
        trigger: "onPlay",
        effects: [
          {
            type: "repeat",
            times: 2,
            effects: [{ type: "damage", target: "opponent", amount: 5, useCombatModifiers: true }],
          },
          { type: "log", text: "{playerName} cuts twice with Mirrored Edge." },
        ],
      },
    ],
  },
};

export const CARD_REWARD_POOL = Object.keys(CARD_LIBRARY).filter(
  (cardId) => !STARTING_DECK.includes(cardId),
);
