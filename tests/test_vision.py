"""Tests for multimodal / vision support."""

import base64
from pathlib import Path

from puterui.vision import (
    build_image_message,
    encode_image_bytes,
    encode_image_file,
    extract_image_refs,
    is_image_path,
)


def test_is_image_path():
    """Should detect image file extensions."""
    assert is_image_path("photo.png") is True
    assert is_image_path("photo.jpg") is True
    assert is_image_path("photo.jpeg") is True
    assert is_image_path("photo.gif") is True
    assert is_image_path("photo.webp") is True
    assert is_image_path("photo.bmp") is True
    assert is_image_path("photo.py") is False
    assert is_image_path("photo.txt") is False
    assert is_image_path("photo") is False


def test_encode_image_file(tmp_path):
    """Should base64-encode an image file."""
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    result = encode_image_file(img)
    assert result is not None
    # Verify it's valid base64
    decoded = base64.b64decode(result)
    assert decoded.startswith(b"\x89PNG")


def test_encode_image_file_nonexistent():
    """Should return None for missing files."""
    assert encode_image_file(Path("/nonexistent/img.png")) is None


def test_encode_image_file_wrong_extension(tmp_path):
    """Should return None for non-image extensions."""
    txt = tmp_path / "file.txt"
    txt.write_text("not an image")
    assert encode_image_file(txt) is None


def test_encode_image_bytes():
    """Should encode raw bytes."""
    data = b"\x89PNG\r\n\x1a\n"
    result = encode_image_bytes(data)
    assert base64.b64decode(result) == data


def test_build_image_message(tmp_path):
    """Should build a message with images."""
    img = tmp_path / "screenshot.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

    msg = build_image_message(
        "What's in this?",
        [str(img)],
        project_dir=tmp_path,
    )
    assert msg["role"] == "user"
    assert msg["content"] == "What's in this?"
    assert "images" in msg
    assert len(msg["images"]) == 1


def test_build_image_message_missing_file(tmp_path):
    """Should build message without images if files are missing."""
    msg = build_image_message(
        "What's in this?",
        [str(tmp_path / "nonexistent.png")],
        project_dir=tmp_path,
    )
    assert msg["content"] == "What's in this?"
    assert "images" not in msg


def test_extract_image_refs_tag():
    """Should extract [image: path] tags."""
    text = "Look at [image: screenshot.png] and tell me what you see"
    cleaned, paths = extract_image_refs(text)
    assert "screenshot.png" in paths
    assert "[image:" not in cleaned


def test_extract_image_refs_bare_path():
    """Should detect bare image paths with prefix."""
    text = "analyze ./screenshot.png please"
    cleaned, paths = extract_image_refs(text)
    assert "./screenshot.png" in paths
    # Path should be removed from cleaned text
    assert "./screenshot.png" not in cleaned
    assert "analyze" in cleaned


def test_extract_image_refs_bare_filename():
    """Should detect bare filenames without path prefix."""
    text = "what is in screenshot.png"
    cleaned, paths = extract_image_refs(text)
    assert "screenshot.png" in paths
    assert "screenshot.png" not in cleaned


def test_extract_image_refs_nested_path():
    """Should detect paths with directories."""
    text = "check images/photo.jpg for issues"
    cleaned, paths = extract_image_refs(text)
    assert "images/photo.jpg" in paths


def test_extract_image_refs_no_images():
    """Should return empty list when no images."""
    text = "just a normal message"
    cleaned, paths = extract_image_refs(text)
    assert paths == []
    assert cleaned == "just a normal message"


def test_extract_image_refs_multiple():
    """Should handle multiple images."""
    text = "[image: a.png] compare with [image: b.jpg]"
    cleaned, paths = extract_image_refs(text)
    assert "a.png" in paths
    assert "b.jpg" in paths
    assert len(paths) == 2
