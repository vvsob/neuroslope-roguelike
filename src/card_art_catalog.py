from pathlib import Path

GENERATED_CARD_DIR = Path(__file__).resolve().parent / "assets" / "generated" / "cards"

CARD_NEGATIVE_PROMPT = (
    "text, letters, logo, watermark, border, frame, ui, hud, multiple panels, photorealistic, "
    "3d render, blurry, low detail, cluttered background, cropped subject"
)

CARD_ART_CATALOG = {
    "strike": {
        "path": GENERATED_CARD_DIR / "strike.png",
        "prompt": (
            "fantasy action card illustration, Strike, lone warrior blade cutting through sparks in a fast diagonal slash, "
            "aggressive motion trail, crimson steel light, dark fantasy roguelike card art, dramatic composition, painterly style"
        ),
    },
    "defend": {
        "path": GENERATED_CARD_DIR / "defend.png",
        "prompt": (
            "fantasy action card illustration, Defend, armored guardian behind a rune shield wall, bronze barrier catching enemy blows, "
            "protective stance, dark fantasy roguelike card art, dramatic composition, painterly style"
        ),
    },
    "bash": {
        "path": GENERATED_CARD_DIR / "bash.png",
        "prompt": (
            "fantasy action card illustration, Bash, brutal shield ram smashing into a monster jaw, heavy impact burst, fractured armor shards, "
            "close combat violence, dark fantasy roguelike card art, dramatic painterly style"
        ),
    },
    "focus": {
        "path": GENERATED_CARD_DIR / "focus.png",
        "prompt": (
            "fantasy action card illustration, Focus, warrior meditating amid floating sigils and blue ember light, sharpened gaze, "
            "mind and body alignment, dark fantasy roguelike card art, mystical painterly style"
        ),
    },
    "quick_slash": {
        "path": GENERATED_CARD_DIR / "quick_slash.png",
        "prompt": (
            "fantasy action card illustration, Quick Slash, twin afterimages of a fighter cutting past an enemy in one swift motion, "
            "silver speed lines, agile attack, dark fantasy roguelike card art, energetic painterly style"
        ),
    },
    "iron_shell": {
        "path": GENERATED_CARD_DIR / "iron_shell.png",
        "prompt": (
            "fantasy action card illustration, Iron Shell, dense metal plating growing over a fighter like living armor, "
            "molten seams cooling into steel, defensive magic, dark fantasy roguelike card art, painterly style"
        ),
    },
    "cleave": {
        "path": GENERATED_CARD_DIR / "cleave.png",
        "prompt": (
            "fantasy action card illustration, Cleave, huge sweeping axe arc crossing the whole battlefield, orange sparks and torn shadows, "
            "wide devastating slash, dark fantasy roguelike card art, dramatic painterly style"
        ),
    },
    "second_wind": {
        "path": GENERATED_CARD_DIR / "second_wind.png",
        "prompt": (
            "fantasy action card illustration, Second Wind, wounded fighter rising in a healing gust of pale green and gold spirit smoke, "
            "restoration and grit, dark fantasy roguelike card art, painterly style"
        ),
    },
}
