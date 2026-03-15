export const CARD_ART = {
  strike: {
    title: "Strike",
    image: "./src/assets/generated/cards/strike.png",
    fallback: "./src/assets/player-placeholder.svg",
  },
  defend: {
    title: "Defend",
    image: "./src/assets/generated/cards/defend.png",
    fallback: "./src/assets/player-placeholder.svg",
  },
  bash: {
    title: "Bash",
    image: "./src/assets/generated/cards/bash.png",
    fallback: "./src/assets/generated/cards/strike.png",
  },
  focus: {
    title: "Focus",
    image: "./src/assets/generated/cards/focus.png",
    fallback: "./src/assets/enemy-placeholder.svg",
  },
  quick_slash: {
    title: "Quick Slash",
    image: "./src/assets/generated/cards/quick_slash.png",
    fallback: "./src/assets/generated/cards/strike.png",
  },
  iron_shell: {
    title: "Iron Shell",
    image: "./src/assets/generated/cards/iron_shell.png",
    fallback: "./src/assets/player-placeholder.svg",
  },
  cleave: {
    title: "Cleave",
    image: "./src/assets/generated/cards/cleave.png",
    fallback: "./src/assets/generated/cards/strike.png",
  },
  second_wind: {
    title: "Second Wind",
    image: "./src/assets/generated/cards/second_wind.png",
    fallback: "./src/assets/enemy-placeholder.svg",
  },
};

export function getCardArt(cardId) {
  return (
    CARD_ART[cardId] ?? {
      title: "Card Art",
      image: "./src/assets/player-placeholder.svg",
      fallback: "./src/assets/player-placeholder.svg",
    }
  );
}
