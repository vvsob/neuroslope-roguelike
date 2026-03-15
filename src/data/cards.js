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
    name: "Удар",
    cost: 1,
    type: "Attack",
    rarity: "Starter",
    description: "Нанести 6 урона.",
    behaviors: [
      {
        trigger: "onPlay",
        effects: [
          { type: "damage", target: "opponent", amount: 6, useCombatModifiers: true },
          { type: "log", text: "{playerName} бьёт на 6." },
        ],
      },
    ],
  },
  defend: {
    id: "defend",
    name: "Защита",
    cost: 1,
    type: "Skill",
    rarity: "Starter",
    description: "Получить 5 блока.",
    behaviors: [
      {
        trigger: "onPlay",
        effects: [
          { type: "modifyStat", target: "self", stat: "block", amount: 5 },
          { type: "log", text: "{playerName} уходит в блок на 5." },
        ],
      },
    ],
  },
  bash: {
    id: "bash",
    name: "Дробление",
    cost: 2,
    type: "Attack",
    rarity: "Starter",
    description: "Нанести 8 урона. Наложить 2 Уязвимости.",
    behaviors: [
      {
        trigger: "onPlay",
        effects: [
          { type: "damage", target: "opponent", amount: 8, useCombatModifiers: true },
          { type: "modifyStat", target: "opponent", stat: "vulnerable", amount: 2 },
          { type: "log", text: "{playerName} дробит на 8 и накладывает Уязвимость." },
        ],
      },
    ],
  },
  focus: {
    id: "focus",
    name: "Концентрация",
    cost: 1,
    type: "Skill",
    rarity: "Starter",
    description: "Получить 2 Силы в этом бою.",
    behaviors: [
      {
        trigger: "onPlay",
        effects: [
          { type: "modifyStat", target: "self", stat: "strength", amount: 2 },
          { type: "log", text: "{playerName} сосредотачивается. +2 Силы." },
        ],
      },
    ],
  },
  quick_slash: {
    id: "quick_slash",
    name: "Быстрый клинок",
    cost: 1,
    type: "Attack",
    rarity: "Common",
    description: "Нанести 7 урона. Взять 1 карту.",
    behaviors: [
      {
        trigger: "onPlay",
        effects: [
          { type: "damage", target: "opponent", amount: 7, useCombatModifiers: true },
          { type: "drawCards", amount: 1 },
          { type: "log", text: "{playerName} наносит быстрый удар и тянет карту." },
        ],
      },
    ],
  },
  iron_shell: {
    id: "iron_shell",
    name: "Железный панцирь",
    cost: 1,
    type: "Skill",
    rarity: "Common",
    description: "Получить 7 блока. +1 Металлизация.",
    behaviors: [
      {
        trigger: "onPlay",
        effects: [
          { type: "modifyStat", target: "self", stat: "block", amount: 7 },
          { type: "modifyStat", target: "self", stat: "metallicize", amount: 1 },
          { type: "log", text: "{playerName} укрепляет броню. Блок +7, Металлизация +1." },
        ],
      },
    ],
  },
  cleave: {
    id: "cleave",
    name: "Рассечение",
    cost: 1,
    type: "Attack",
    rarity: "Common",
    description: "Нанести 9 урона всем врагам.",
    behaviors: [
      {
        trigger: "onPlay",
        effects: [
          { type: "damage", target: "allEnemies", amount: 9, useCombatModifiers: true },
          { type: "log", text: "{playerName} рассекает весь ряд врагов на 9." },
        ],
      },
    ],
  },
  second_wind: {
    id: "second_wind",
    name: "Второе дыхание",
    cost: 1,
    type: "Skill",
    rarity: "Common",
    description: "Восстановить 4 HP. Изгнать.",
    keywords: ["exhaust"],
    behaviors: [
      {
        trigger: "onPlay",
        effects: [
          { type: "heal", target: "self", amount: 4 },
          { type: "log", text: "{playerName} восстанавливает 4 HP." },
        ],
      },
    ],
  },
  ember_script: {
    id: "ember_script",
    name: "Жаровня",
    cost: 1,
    type: "Skill",
    rarity: "Uncommon",
    description: "При взятии: получить 1 Энергию. Изгнать.",
    keywords: ["exhaust"],
    behaviors: [
      {
        trigger: "onDraw",
        effects: [
          { type: "gainEnergy", amount: 1 },
          { type: "log", text: "Жаровня вспыхивает в руке. +1 Энергия." },
        ],
      },
    ],
  },
  mirrored_edge: {
    id: "mirrored_edge",
    name: "Зеркальный клинок",
    cost: 1,
    type: "Attack",
    rarity: "Uncommon",
    description: "Нанести 5 урона дважды.",
    behaviors: [
      {
        trigger: "onPlay",
        effects: [
          {
            type: "repeat",
            times: 2,
            effects: [{ type: "damage", target: "opponent", amount: 5, useCombatModifiers: true }],
          },
          { type: "log", text: "{playerName} дважды бьёт зеркальным клинком." },
        ],
      },
    ],
  },
};

export const CARD_REWARD_POOL = Object.keys(CARD_LIBRARY).filter(
  (cardId) => !STARTING_DECK.includes(cardId),
);
