"""
Async image generation via Google Gemini (Nano Banana / Flash Image).

Used to generate art for LLM-created enemies and weapons at run start.
Images are saved to src/assets/generated/run/{node_id}-{kind}.png
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

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


def _get_gemini_key() -> Optional[str]:
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

    return _os.environ.get("GEMINI_API_KEY") or _os.environ.get("GOOGLE_API_KEY")


def _generate_one_sync(prompt: str, negative_prompt: str, output_path: Path) -> None:
    """Synchronous generation of a single image. Called in a thread pool."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        logger.error("google-genai not installed — skipping image generation")
        return

    api_key = _get_gemini_key()
    if not api_key:
        logger.warning(
            "GEMINI_API_KEY/GOOGLE_API_KEY not set — skipping image generation for %s",
            output_path.name,
        )
        return

    model = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    client = genai.Client(api_key=api_key)

    merged_prompt = f"{prompt}\n\nAvoid: {negative_prompt}"
    logger.info("Gemini image gen start: model=%s output=%s", model, output_path.name)
    logger.debug("Prompt for %s:\n%s", output_path.name, merged_prompt)

    try:
        response = client.models.generate_content(
            model=model,
            contents=[merged_prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio="1:1"),
            ),
        )
    except Exception:
        logger.exception("Gemini request failed for %s", output_path.name)
        return

    parts = getattr(response, "parts", None)
    candidates = getattr(response, "candidates", None)
    if not parts and candidates:
        parts = candidates[0].content.parts

    if not parts:
        logger.warning("Gemini returned no parts for %s. Response: %r", output_path.name, response)
        return

    candidate_count = len(candidates) if candidates else 0
    part_kinds = [type(part).__name__ for part in parts]
    logger.info(
        "Gemini response for %s: candidates=%d parts=%s",
        output_path.name,
        candidate_count,
        part_kinds,
    )

    for part in parts:
        inline = getattr(part, "inline_data", None)
        if inline is None:
            text = getattr(part, "text", None)
            if text:
                logger.debug("Gemini non-image part for %s: %s", output_path.name, text[:240])
            continue
        try:
            image = part.as_image()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(output_path)
            logger.info("Generated %s", output_path.name)
            return
        except Exception:
            logger.exception("Failed to decode/save Gemini image for %s", output_path.name)
            return

    logger.warning("Gemini returned no image data for %s", output_path.name)


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
        logger.exception("Image generation failed for %s", path.name)
