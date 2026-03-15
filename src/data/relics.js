export const RELIC_LIBRARY = {
  battle_battery: {
    id: "battle_battery",
    name: "Battle Battery",
    icon: "⚡",
    description: "At the start of each battle, gain 1 Energy.",
    behaviors: [
      {
        trigger: "onBattleStart",
        effects: [
          { type: "gainEnergy", amount: 1 },
          { type: "log", text: "{sourceName} crackles. Gain 1 Energy." },
        ],
      },
    ],
  },
  thorn_sigil: {
    id: "thorn_sigil",
    name: "Thorn Sigil",
    icon: "✶",
    description: "Whenever you play a card, gain 1 Block.",
    behaviors: [
      {
        trigger: "onCardPlayed",
        effects: [
          { type: "modifyStat", target: "player", stat: "block", amount: 1 },
          { type: "log", text: "{sourceName} grants 1 Block." },
        ],
      },
    ],
  },
  ember_idol: {
    id: "ember_idol",
    name: "Ember Idol",
    icon: "🔥",
    description: "At the start of your turn, gain 1 Strength.",
    behaviors: [
      {
        trigger: "onTurnStart",
        effects: [
          { type: "modifyStat", target: "player", stat: "strength", amount: 1 },
          { type: "log", text: "{sourceName} warms your blood. Gain 1 Strength." },
        ],
      },
    ],
  },
};

export const TREASURE_RELIC_POOL = Object.keys(RELIC_LIBRARY);
