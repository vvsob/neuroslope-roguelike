import argparse
import os
from pathlib import Path

from card_art_catalog import CARD_ART_CATALOG, CARD_NEGATIVE_PROMPT
from level_art_catalog import (
    ENEMY_NEGATIVE_PROMPT,
    LEVEL_ART_CATALOG,
    WEAPON_NEGATIVE_PROMPT,
)


def load_env_file(path: Path):
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _get_api_key() -> str:
    repo_root = Path(__file__).resolve().parent.parent
    load_env_file(repo_root / ".env")
    load_env_file(repo_root / ".env.local")
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("Set GEMINI_API_KEY (or GOOGLE_API_KEY) in the environment or in .env/.env.local.")
    return api_key


def build_client():
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("google-genai is not installed. Add it to your dependencies.") from exc

    return genai.Client(api_key=_get_api_key())


def iter_targets(level: str | None, kind: str):
    keys = [level] if level else list(LEVEL_ART_CATALOG.keys())
    for key in keys:
        entry = LEVEL_ART_CATALOG[key]
        if kind in {"weapon", "all"}:
            yield key, "weapon", entry["weapon_prompt"], entry["weapon_path"], WEAPON_NEGATIVE_PROMPT
        if kind in {"enemy", "all"}:
            yield key, "enemy", entry["enemy_prompt"], entry["enemy_path"], ENEMY_NEGATIVE_PROMPT
    if kind in {"card", "all"}:
        for card_id, entry in CARD_ART_CATALOG.items():
            yield card_id, "card", entry["prompt"], entry["path"], CARD_NEGATIVE_PROMPT


def generate_image(client, prompt: str, negative_prompt: str):
    from google.genai import types

    model = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    merged_prompt = f"{prompt}\n\nAvoid: {negative_prompt}"
    response = client.models.generate_content(
        model=model,
        contents=[merged_prompt],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="1:1"),
        ),
    )

    parts = getattr(response, "parts", None)
    candidates = getattr(response, "candidates", None)
    if not parts and candidates:
        parts = candidates[0].content.parts

    if not parts:
        raise RuntimeError("Gemini returned no image parts.")

    for part in parts:
        inline = getattr(part, "inline_data", None)
        if inline is None:
            continue
        return part.as_image()

    raise RuntimeError("Gemini returned no image data.")


def main():
    parser = argparse.ArgumentParser(description="Generate level weapon, enemy, and card art.")
    parser.add_argument("--level", choices=LEVEL_ART_CATALOG.keys())
    parser.add_argument("--kind", choices=("weapon", "enemy", "card", "all"), default="all")
    args = parser.parse_args()

    client = build_client()

    for level_key, kind, prompt, output_path, negative_prompt in iter_targets(args.level, args.kind):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        image = generate_image(client, prompt, negative_prompt)
        image.save(path)
        print(f"{level_key} {kind}: {path}")


if __name__ == "__main__":
    main()
