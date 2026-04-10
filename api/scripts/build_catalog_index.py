from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

import numpy as np


def _read_metadata(csv_path: Path) -> list[dict]:
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader]

    required = {"product_id", "title", "category", "image_filename"}
    missing = required - set(reader.fieldnames or [])
    if missing:
        raise RuntimeError(f"metadata.csv missing columns: {sorted(missing)}")

    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", required=True, help="Path to catalog images dir")
    parser.add_argument("--metadata", required=True, help="Path to metadata.csv")
    parser.add_argument("--out", required=True, help="Output dir for artifacts")
    parser.add_argument(
        "--model",
        default=None,
        help="Embedding model: resnet50 (default) or clip",
    )
    args = parser.parse_args()

    images_dir = Path(args.images).resolve()
    metadata_path = Path(args.metadata).resolve()
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = _read_metadata(metadata_path)

    from app.vision.embeddings import embed_image_bytes

    vectors: list[np.ndarray] = []
    meta: list[dict] = []

    for r in rows:
        image_filename = r["image_filename"]
        image_path = images_dir / image_filename
        if not image_path.exists():
            raise RuntimeError(f"Missing image: {image_path}")

        image_bytes = image_path.read_bytes()
        v = embed_image_bytes(image_bytes, model=args.model)
        vectors.append(v)

        item = {
            "product_id": r.get("product_id"),
            "title": r.get("title"),
            "category": r.get("category"),
            "price": r.get("price"),
            "url": r.get("url"),
            "image_filename": image_filename,
            "image_key": f"catalog/images/{image_filename}",
        }
        meta.append(item)

    X = np.stack(vectors).astype("float32")
    d = X.shape[1]

    import faiss  # type: ignore

    index = faiss.IndexFlatIP(d)
    index.add(X)

    faiss.write_index(index, str(out_dir / "index.faiss"))
    np.save(str(out_dir / "vectors.npy"), X)
    with open(out_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f)

    print(f"Wrote {len(meta)} items")
    print(f"- {out_dir / 'index.faiss'}")
    print(f"- {out_dir / 'vectors.npy'}")
    print(f"- {out_dir / 'metadata.json'}")


if __name__ == "__main__":
    main()
