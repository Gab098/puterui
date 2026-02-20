"""Multimodal / vision support for PuterUI.

Handles encoding images for Ollama's vision-capable models (e.g.
MiniCPM-o-4_5, llava, moondream, bakllava). Ollama expects images
as base64-encoded strings in the message's `images` field.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional

# Image formats supported by Ollama vision models
SUPPORTED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".tif",
}

# Maximum image size in bytes (20MB)
MAX_IMAGE_SIZE = 20 * 1024 * 1024


def is_image_path(path_str: str) -> bool:
    """Check if a path looks like an image file."""
    p = Path(path_str)
    return p.suffix.lower() in SUPPORTED_EXTENSIONS


def encode_image_file(path: Path) -> Optional[str]:
    """Read and base64-encode an image file.

    Returns the base64 string or None on failure.
    """
    if not path.exists() or not path.is_file():
        return None

    if path.stat().st_size > MAX_IMAGE_SIZE:
        return None

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return None

    try:
        data = path.read_bytes()
        return base64.b64encode(data).decode("ascii")
    except Exception:
        return None


def encode_image_bytes(data: bytes) -> str:
    """Base64-encode raw image bytes."""
    return base64.b64encode(data).decode("ascii")


def build_image_message(
    text: str,
    image_paths: list[str],
    project_dir: Optional[Path] = None,
) -> dict:
    """Build an Ollama message dict with text and images.

    Ollama format:
    {
        "role": "user",
        "content": "What's in this image?",
        "images": ["base64string1", "base64string2"]
    }
    """
    images: list[str] = []

    for img_path in image_paths:
        p = Path(img_path)
        if not p.is_absolute() and project_dir:
            p = project_dir / p

        encoded = encode_image_file(p.resolve())
        if encoded:
            images.append(encoded)

    message: dict = {"role": "user", "content": text}
    if images:
        message["images"] = images

    return message


def extract_image_refs(text: str) -> tuple[str, list[str]]:
    """Extract image file references from user text.

    Supports:
    - Inline paths: "analyze this image ./screenshot.png"
    - Explicit tags: "[image: path/to/file.png]"

    Returns (cleaned_text, list_of_image_paths).
    """
    import re

    image_paths: list[str] = []

    # Extract [image: path] tags
    tag_pattern = r'\[image:\s*([^\]]+)\]'
    for match in re.finditer(tag_pattern, text):
        path = match.group(1).strip()
        if is_image_path(path):
            image_paths.append(path)

    # Remove tags from text
    cleaned = re.sub(tag_pattern, '', text).strip()

    # Also detect bare image paths in the text
    word_pattern = r'(?:^|\s)((?:\./|/|\.\./)?\S+\.(?:png|jpg|jpeg|gif|bmp|webp|tiff|tif))'
    for match in re.finditer(word_pattern, cleaned, re.IGNORECASE):
        path = match.group(1).strip()
        if path not in image_paths:
            image_paths.append(path)

    return cleaned, image_paths
