from pathlib import Path

GENERATED_DIR = Path(__file__).resolve().parent / "assets" / "generated"

WEAPON_NEGATIVE_PROMPT = (
    "character, hand holding weapon, enemy, creature, ui, hud, text, letters, watermark, logo, "
    "border, frame, collage, photorealistic, 3d render, low detail, blurry, cluttered composition"
)

ENEMY_NEGATIVE_PROMPT = (
    "weapon only, multiple enemies, ui, hud, text, letters, watermark, logo, border, frame, "
    "photorealistic, 3d render, modern clothing, guns, sci-fi soldier, blurry face, cropped head"
)

LEVEL_ART_CATALOG = {
    "n1": {
        "label": "Floor 1 Hallway",
        "weapon_path": GENERATED_DIR / "n1-weapon.png",
        "enemy_path": GENERATED_DIR / "n1-enemy.png",
        "weapon_prompt": (
            "single fantasy dagger, Scrapfang Shiv, trench knife made from rusty rail scrap and pale beast bone, "
            "jagged chipped edge, wrapped leather grip, soot stains, ember sparks, dark fantasy roguelike item art, "
            "centered composition, isolated weapon, hand-painted painterly brushwork, readable silhouette, plain backdrop"
        ),
        "enemy_prompt": (
            "single enemy portrait, Cinder Rat Brute, hulking tunnel rat monster standing upright, charred fur, ember-lit eyes, "
            "scarred muzzle, iron scraps strapped to shoulders, ash drifting in the air, dark fantasy roguelike battle art, "
            "full body, centered composition, painterly hand-painted style, readable silhouette, plain atmospheric background"
        ),
    },
    "n2": {
        "label": "Floor 2 Hallway",
        "weapon_path": GENERATED_DIR / "n2-weapon.png",
        "enemy_path": GENERATED_DIR / "n2-enemy.png",
        "weapon_prompt": (
            "single fantasy spear, Static Pike, long steel pike with cracked copper coils and a blue storm crystal, "
            "faint electric arcs, worn grip wraps, relic weapon from a ruined spire, dark fantasy roguelike item art, "
            "centered composition, isolated weapon, painterly shading, readable silhouette, plain backdrop"
        ),
        "enemy_prompt": (
            "single enemy portrait, Lantern Stalker, gaunt humanoid hunter in torn cloaks and hanging chains, "
            "carrying a poisoned lantern with sickly green glow, long limbs, masked face, dark fantasy roguelike battle art, "
            "full body, centered composition, painterly hand-painted style, readable silhouette, atmospheric background"
        ),
    },
    "n3": {
        "label": "Floor 3 Campfire",
        "weapon_path": GENERATED_DIR / "n3-weapon.png",
        "enemy_path": GENERATED_DIR / "n3-enemy.png",
        "weapon_prompt": (
            "single fantasy sword, Ashen Hookblade, curved hooked blade blackened by campfire soot, iron teeth near the spine, "
            "glowing ember runes in the fuller, survivalist dark fantasy roguelike item art, centered composition, isolated item, "
            "painterly brushwork, readable silhouette, plain backdrop"
        ),
        "enemy_prompt": (
            "single enemy portrait, Pyre Sentinel, dormant guardian made of charcoal stone and cracked kiln plates, "
            "orange heat glowing from seams, standing watch near an ancient fire pit, dark fantasy roguelike battle art, "
            "full body, centered composition, painterly hand-painted style, readable silhouette, atmospheric background"
        ),
    },
    "n4": {
        "label": "Floor 4 Treasure",
        "weapon_path": GENERATED_DIR / "n4-weapon.png",
        "enemy_path": GENERATED_DIR / "n4-enemy.png",
        "weapon_prompt": (
            "single fantasy dagger, Prism Cutter, elegant relic knife with crystal glass edge, brass hilt, refracted cold light, "
            "tiny spectral shards hovering nearby, treasure vault dark fantasy roguelike item art, centered composition, isolated item, "
            "painterly shading, readable silhouette, plain backdrop"
        ),
        "enemy_prompt": (
            "single enemy portrait, Vault Mimic, treasure chamber horror with gilded shell plates, false jewel eyes, "
            "split maw hidden under a chest-like carapace, creeping pose, dark fantasy roguelike battle art, full body, "
            "centered composition, painterly hand-painted style, readable silhouette, atmospheric background"
        ),
    },
    "n5": {
        "label": "Floor 5 Elite",
        "weapon_path": GENERATED_DIR / "n5-weapon.png",
        "enemy_path": GENERATED_DIR / "n5-enemy.png",
        "weapon_prompt": (
            "single fantasy hammer, Siegebreaker Maul, heavy bronze war maul with engraved impact runes, hydraulic braces, "
            "battle dents, chained pommel, elite dark fantasy roguelike item art, centered composition, isolated weapon, "
            "painterly hand-painted style, readable silhouette, plain backdrop"
        ),
        "enemy_prompt": (
            "single enemy portrait, Bronze Husk Prime, towering war construct with cracked bronze armor, molten seams, "
            "one massive crushing arm and furnace core in the chest, dark fantasy roguelike battle art, full body, centered composition, "
            "painterly hand-painted style, readable silhouette, atmospheric background"
        ),
    },
    "n6": {
        "label": "Floor 6 Boss",
        "weapon_path": GENERATED_DIR / "n6-weapon.png",
        "enemy_path": GENERATED_DIR / "n6-enemy.png",
        "weapon_prompt": (
            "single fantasy spear, Neurolance, ceremonial spear built around a living crystal spine and blue neural filaments, "
            "obsidian grip, silver ritual fittings, psychic glow, boss-tier dark fantasy roguelike item art, centered composition, "
            "isolated weapon, painterly shading, readable silhouette, plain backdrop"
        ),
        "enemy_prompt": (
            "single enemy portrait, The Neurolith, colossal psychic monolith suspended by cables and stone rings, "
            "cold blue fire, fractured mask-like face, floating shards and ritual machinery, dark fantasy roguelike boss art, "
            "full body, centered composition, painterly hand-painted style, readable silhouette, atmospheric background"
        ),
    },
}
