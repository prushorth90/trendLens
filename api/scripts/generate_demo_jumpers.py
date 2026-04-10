from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image, ImageDraw


def _make_jumper(path: Path, *, bg: tuple[int, int, int], body: tuple[int, int, int]) -> None:
    img = Image.new("RGB", (512, 512), bg)
    d = ImageDraw.Draw(img)

    # torso
    d.rounded_rectangle([155, 145, 357, 430], radius=18, fill=body)
    # sleeves
    d.rounded_rectangle([95, 175, 155, 335], radius=18, fill=body)
    d.rounded_rectangle([357, 175, 417, 335], radius=18, fill=body)
    # neck opening
    d.ellipse([230, 130, 282, 180], fill=bg)
    # cuffs + waistband (slightly darker)
    cuff = tuple(max(0, int(c * 0.85)) for c in body)
    d.rectangle([95, 320, 155, 335], fill=cuff)
    d.rectangle([357, 320, 417, 335], fill=cuff)
    d.rectangle([155, 415, 357, 430], fill=cuff)

    img.save(path, format="JPEG", quality=92)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    images_dir = repo_root / "catalog" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = repo_root / "catalog" / "metadata.csv"

    bg = (245, 245, 245)
    items = [
        ("jumper-001", "Green Jumper", "jumpers", "jumper_green.jpg", "59.00", "", bg, (30, 140, 70)),
        ("jumper-002", "Black Jumper", "jumpers", "jumper_black.jpg", "59.00", "", bg, (25, 25, 25)),
        ("jumper-003", "Gray Jumper", "jumpers", "jumper_gray.jpg", "59.00", "", bg, (120, 120, 120)),
        ("jumper-004", "Blue Jumper", "jumpers", "jumper_blue.jpg", "59.00", "", bg, (40, 80, 200)),
        ("jumper-005", "Red Jumper", "jumpers", "jumper_red.jpg", "59.00", "", bg, (190, 40, 40)),
        ("jumper-006", "Green Jumper (Alt)", "jumpers", "jumper_green2.jpg", "62.00", "", (235, 235, 235), (40, 160, 80)),
    ]

    for _pid, _title, _cat, filename, *_rest, bgc, body in items:
        _make_jumper(images_dir / filename, bg=bgc, body=body)

    with open(metadata_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["product_id", "title", "category", "image_filename", "price", "url"])
        for pid, title, cat, filename, price, url, *_ in items:
            w.writerow([pid, title, cat, filename, price, url])

    print(f"Wrote demo jumper images to: {images_dir}")
    print(f"Wrote metadata to: {metadata_path}")


if __name__ == "__main__":
    main()
