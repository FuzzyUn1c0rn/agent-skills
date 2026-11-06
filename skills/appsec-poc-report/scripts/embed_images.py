#!/usr/bin/env python3
"""Embed approved local images in a Markdown report without printing image data."""

import argparse
import base64
import hashlib
import html
import os
from pathlib import Path
import re
import tempfile


PLACEHOLDER = re.compile(r"\{\{INLINE_IMAGE:([^|}]+)\|([^}]+)\}\}")


def image_mime(path: Path, data: bytes) -> str:
    suffix = path.suffix.lower()
    if suffix == ".png" and data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if suffix in {".jpg", ".jpeg"} and data.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if suffix == ".webp" and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    raise ValueError(f"Unsupported or mismatched image format: {path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Markdown report containing INLINE_IMAGE placeholders")
    parser.add_argument("--image-root", required=True, type=Path, help="Approved image directory")
    args = parser.parse_args()

    report = args.report.resolve(strict=True)
    image_root = args.image_root.resolve(strict=True)
    if not image_root.is_dir():
        parser.error("--image-root must be a directory")

    source = report.read_text(encoding="utf-8")
    matches = list(PLACEHOLDER.finditer(source))
    if not matches:
        parser.error("The report contains no INLINE_IMAGE placeholders")

    records = []

    def replace(match: re.Match[str]) -> str:
        relative_name = match.group(1).strip()
        alt = match.group(2).strip()
        if not relative_name or not alt:
            raise ValueError("Each image needs a relative filename and alt text")
        image = (image_root / relative_name).resolve(strict=True)
        try:
            image.relative_to(image_root)
        except ValueError as exc:
            raise ValueError(f"Image is outside --image-root: {relative_name}") from exc
        if not image.is_file():
            raise ValueError(f"Image is not a file: {relative_name}")

        data = image.read_bytes()
        mime = image_mime(image, data)
        encoded = base64.b64encode(data).decode("ascii")
        if base64.b64decode(encoded, validate=True) != data:
            raise ValueError(f"Image round-trip failed: {relative_name}")
        digest = hashlib.sha256(data).hexdigest()
        records.append((relative_name, len(data), digest))
        return (
            f'<img alt="{html.escape(alt, quote=True)}" '
            f'src="data:{mime};base64,{encoded}" '
            'style="max-width:100%;height:auto">'
        )

    rendered = PLACEHOLDER.sub(replace, source)
    if "{{INLINE_IMAGE:" in rendered:
        raise ValueError("Unresolved INLINE_IMAGE placeholder remains")

    fd, temporary = tempfile.mkstemp(prefix=f".{report.name}.", suffix=".tmp", dir=report.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as output:
            output.write(rendered)
        os.replace(temporary, report)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

    for name, size, digest in records:
        print(f"{name}\tbytes={size}\tsha256={digest}")


if __name__ == "__main__":
    main()
