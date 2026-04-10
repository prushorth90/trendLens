from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image, ImageDraw


def _make_image(path: Path, *, base: tuple[int, int, int], accent: tuple[int, int, int]) -> None:
    img = Image.new("RGB", (512, 512), base)
    draw = ImageDraw.Draw(img)

    # simple "tee" silhouette-ish block (still synthetic)
    draw.rectangle([140, 120, 372, 420], fill=accent)
    draw.rectangle([90, 150, 140, 300], fill=accent)
    draw.rectangle([372, 150, 422, 300], fill=accent)

    img.save(path, format="JPEG", quality=92)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    images_dir = repo_root / "catalog" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = repo_root / "catalog" / "metadata.csv"

    items = [
        ("demo-001", "Red Tee", "tops", "demo_red.jpg", "19.00", "" , (245, 245, 245), (200, 40, 40)),
        ("demo-002", "Blue Tee", "tops", "demo_blue.jpg", "19.00", "" , (245, 245, 245), (40, 80, 200)),
        ("demo-003", "Green Tee", "tops", "demo_green.jpg", "19.00", "" , (245, 245, 245), (40, 160, 80)),
        ("demo-004", "Black Tee", "tops", "demo_black.jpg", "19.00", "" , (245, 245, 245), (30, 30, 30)),
        ("demo-005", "Gray Tee", "tops", "demo_gray.jpg", "19.00", "" , (245, 245, 245), (120, 120, 120)),
        ("demo-006", "Red Tee (Alt)", "tops", "demo_red2.jpg", "21.00", "" , (235, 235, 235), (210, 50, 50)),
    ]

    for _, _, _, filename, *_rest, bg, accent in items:
        _make_image(images_dir / filename, base=bg, accent=accent)

    with open(metadata_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["product_id", "title", "category", "image_filename", "price", "url"])
        for pid, title, cat, filename, price, url, *_ in items:
            w.writerow([pid, title, cat, filename, price, url])

    print(f"Wrote demo catalog images to: {images_dir}")
    print(f"Wrote metadata to: {metadata_path}")


if __name__ == "__main__":
    main()
