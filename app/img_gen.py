"""
Async image generation via Hugging Face Inference API (Stable Diffusion XL).

Used to generate art for LLM-created enemies and weapons at run start.
Images are saved to src/assets/generated/run/{node_id}-{kind}.png
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Negative prompts (same as original gen_image.py) ─────────────────────────

WEAPON_NEGATIVE_PROMPT = (
    "character, hand holding weapon, enemy, creature, ui, hud, text, letters, watermark, logo, "
    "border, frame, collage, photorealistic, 3d render, low detail, blurry, cluttered composition"
)

ENEMY_NEGATIVE_PROMPT = (
    "weapon only, multiple enemies, ui, hud, text, letters, watermark, logo, border, frame, "
    "photorealistic, 3d render, modern clothing, guns, sci-fi soldier, blurry face, cropped head"
)

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "src" / "assets" / "generated" / "run"


def _get_hf_token() -> Optional[str]:
    from pathlib import Path as P
    import os as _os

    repo_root = P(__file__).resolve().parents[1]
    for env_file in (repo_root / ".env", repo_root / ".env.local"):
        if not env_file.exists():
            continue
        for line in env_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            _os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

    return _os.environ.get("HF_TOKEN")


def _generate_one_sync(prompt: str, negative_prompt: str, output_path: Path) -> None:
    """Synchronous generation of a single image. Called in a thread pool."""
    try:
        from huggingface_hub import InferenceClient
    except ImportError:
        logger.error("huggingface_hub not installed — skipping image generation")
        return

    token = _get_hf_token()
    if not token:
        logger.warning("HF_TOKEN not set — skipping image generation for %s", output_path.name)
        return

    client = InferenceClient(provider="hf-inference", api_key=token)
    image = client.text_to_image(
        prompt=prompt,
        negative_prompt=negative_prompt,
        model="stabilityai/stable-diffusion-xl-base-1.0",
        width=1024,
        height=1024,
        num_inference_steps=20,
        guidance_scale=12,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    logger.info("Generated %s", output_path.name)


async def _generate_one_async(prompt: str, negative_prompt: str, output_path: Path) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        _generate_one_sync,
        prompt,
        negative_prompt,
        output_path,
    )


async def generate_run_images(image_prompts: Dict[str, Dict[str, str]]) -> None:
    """
    Generate weapon and enemy images for a LLM-generated run.

    image_prompts: {
        "n1": {"weapon": "...", "enemy": "..."},
        "n2": {"weapon": "...", "enemy": "..."},
        ...
    }

    Images are saved to src/assets/generated/run/{node_id}-weapon.png etc.
    Runs all generations concurrently. Errors per-image are logged but do not
    abort the whole batch — the frontend falls back to placeholders.
    """
    tasks: List[asyncio.Task] = []

    for node_id, prompts in image_prompts.items():
        for kind in ("weapon", "enemy"):
            prompt = prompts.get(kind, "")
            if not prompt:
                continue
            neg = WEAPON_NEGATIVE_PROMPT if kind == "weapon" else ENEMY_NEGATIVE_PROMPT
            output_path = OUTPUT_DIR / f"{node_id}-{kind}.png"

            # Skip if already generated (cache)
            if output_path.exists():
                logger.debug("Skipping %s — already exists", output_path.name)
                continue

            tasks.append(asyncio.create_task(
                _safe_generate(prompt, neg, output_path),
                name=f"{node_id}-{kind}",
            ))

    if tasks:
        await asyncio.gather(*tasks)


async def _safe_generate(prompt: str, neg: str, path: Path) -> None:
    try:
        await _generate_one_async(prompt, neg, path)
    except Exception as exc:
        logger.warning("Image generation failed for %s: %s", path.name, exc)
