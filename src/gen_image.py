import argparse
import os
from pathlib import Path

from huggingface_hub import InferenceClient

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


def build_client() -> InferenceClient:
    repo_root = Path(__file__).resolve().parent.parent
    load_env_file(repo_root / ".env")
    load_env_file(repo_root / ".env.local")
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        raise RuntimeError("Set HF_TOKEN in the environment or in .env/.env.local before running image generation.")

    return InferenceClient(
        provider="hf-inference",
        api_key=hf_token,
    )


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


def generate_image(client: InferenceClient, prompt: str, negative_prompt: str):
    return client.text_to_image(
        prompt=prompt,
        negative_prompt=negative_prompt,
        model="stabilityai/stable-diffusion-xl-base-1.0",
        width=1024,
        height=1024,
        num_inference_steps=20,
        guidance_scale=12,
    )


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
