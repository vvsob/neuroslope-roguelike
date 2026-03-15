export const RELIC_LIBRARY = {
  battle_battery: {
    id: "battle_battery",
    name: "Боевая батарея",
    icon: "⚡",
    description: "В начале каждого боя получить 1 Энергию.",
    behaviors: [
      {
        trigger: "onBattleStart",
        effects: [
          { type: "gainEnergy", amount: 1 },
          { type: "log", text: "{sourceName} разряжается. +1 Энергия." },
        ],
      },
    ],
  },
  thorn_sigil: {
    id: "thorn_sigil",
    name: "Знак Шипов",
    icon: "✶",
    description: "Каждый раз при розыгрыше карты получать 1 Блок.",
    behaviors: [
      {
        trigger: "onCardPlayed",
        effects: [
          { type: "modifyStat", target: "player", stat: "block", amount: 1 },
          { type: "log", text: "{sourceName} даёт 1 Блок." },
        ],
      },
    ],
  },
  ember_idol: {
    id: "ember_idol",
    name: "Идол Жара",
    icon: "🔥",
    description: "В начале своего хода получать 1 Силу.",
    behaviors: [
      {
        trigger: "onTurnStart",
        effects: [
          { type: "modifyStat", target: "player", stat: "strength", amount: 1 },
          { type: "log", text: "{sourceName} разогревает кровь. +1 Сила." },
        ],
      },
    ],
  },
};

export const TREASURE_RELIC_POOL = Object.keys(RELIC_LIBRARY);
