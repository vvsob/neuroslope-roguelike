export const LEVEL_ART = {
  n1: {
    title: "Floor 1",
    weaponName: "Scrapfang Shiv",
    weaponDescription: "A jagged trench knife pieced together from rail scrap and scorched bone.",
    weaponImage: "./src/assets/generated/n1-weapon.png",
    enemyName: "Cinder Rat Brute",
    enemyDescription: "A smoke-soaked tunnel predator with ember-lit eyes and furnace burns across its hide.",
    enemyImage: "./src/assets/generated/n1-enemy.png",
  },
  n2: {
    title: "Floor 2",
    weaponName: "Static Pike",
    weaponDescription: "A long storm pike wound with cracked copper coils and a lightning focus at the tip.",
    weaponImage: "./src/assets/generated/n2-weapon.png",
    enemyName: "Lantern Stalker",
    enemyDescription: "A thin ruin hunter draped in chains and carrying a poisoned lantern through the fog.",
    enemyImage: "./src/assets/generated/n2-enemy.png",
  },
  n3: {
    title: "Floor 3",
    weaponName: "Ashen Hookblade",
    weaponDescription: "A hooked campfire blade blackened by soot, built for ripping armor in close quarters.",
    weaponImage: "./src/assets/generated/n3-weapon.png",
    enemyName: "Pyre Sentinel",
    enemyDescription: "A dormant guardian formed from charcoal stone, still glowing with buried heat.",
    enemyImage: "./src/assets/generated/n3-enemy.png",
  },
  n4: {
    title: "Floor 4",
    weaponName: "Prism Cutter",
    weaponDescription: "A relic dagger with a crystal edge that bends cold light into razor-thin arcs.",
    weaponImage: "./src/assets/generated/n4-weapon.png",
    enemyName: "Vault Mimic",
    enemyDescription: "A treasure-chamber horror plated in gilded shells and jewel-like false eyes.",
    enemyImage: "./src/assets/generated/n4-enemy.png",
  },
  n5: {
    title: "Floor 5",
    weaponName: "Siegebreaker Maul",
    weaponDescription: "A brutal bronze war maul ringed with impact runes and hydraulic braces.",
    weaponImage: "./src/assets/generated/n5-weapon.png",
    enemyName: "Bronze Husk Prime",
    enemyDescription: "An elite war construct with cracked plating, molten seams, and a crushing frame.",
    enemyImage: "./src/assets/generated/n5-enemy.png",
  },
  n6: {
    title: "Floor 6",
    weaponName: "Neurolance",
    weaponDescription: "A ceremonial spear built around a living crystal spine and pulsing neural filaments.",
    weaponImage: "./src/assets/generated/n6-weapon.png",
    enemyName: "The Neurolith",
    enemyDescription: "A colossal psychic monolith suspended in cables, stone plates, and cold blue fire.",
    enemyImage: "./src/assets/generated/n6-enemy.png",
  },
};

export function getLevelArt(nodeId) {
  return (
    LEVEL_ART[nodeId] ?? {
      title: "Unknown Floor",
      weaponName: "Fallback Blade",
      weaponDescription: "A placeholder weapon illustration.",
      weaponImage: "./src/assets/player-placeholder.svg",
      enemyName: "Unknown Enemy",
      enemyDescription: "A placeholder enemy illustration.",
      enemyImage: "./src/assets/enemy-placeholder.svg",
    }
  );
}
