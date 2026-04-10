from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.aws.s3 import download_to_path, get_object_bytes
from app.config import get_settings
from app.store.jobs import JobsStore


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _artifacts_local_dir() -> Path:
    return _repo_root() / "catalog" / "artifacts"


def _images_local_dir() -> Path:
    return _repo_root() / "catalog" / "images"


def _catalog_artifact_keys(settings) -> tuple[str, str]:
    index_key = f"{settings.catalog_prefix}artifacts/index.faiss"
    meta_key = f"{settings.catalog_prefix}artifacts/metadata.json"
    return index_key, meta_key


def _vectors_key(settings) -> str:
    return f"{settings.catalog_prefix}artifacts/vectors.npy"


def process_image_bytes_local(*, image_bytes: bytes) -> list[dict]:
    settings = get_settings()
    artifacts_dir = _artifacts_local_dir()
    meta_path = artifacts_dir / "metadata.json"
    index_path = artifacts_dir / "index.faiss"
    vectors_path = artifacts_dir / "vectors.npy"

    if not meta_path.exists() or not vectors_path.exists():
        raise RuntimeError(
            "Missing catalog artifacts. Build them first: python -m scripts.build_catalog_index ..."
        )

    from app.vision.embeddings import embed_image_bytes

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    X = np.load(str(vectors_path)).astype("float32")
    q = embed_image_bytes(image_bytes, model=settings.embedding_model).astype("float32")
    scores = X @ q
    idxs = np.argsort(-scores)[:5]

    results: list[dict] = []
    for i in idxs:
        item = dict(meta[int(i)])
        item["score"] = float(scores[int(i)])
        results.append(item)
    return results


def process_s3_event(*, event: dict, store: JobsStore) -> None:
    settings = get_settings()
    if not settings.s3_bucket:
        raise RuntimeError("S3_BUCKET is required")

    records = event.get("Records") or []
    if not records:
        return

    index_key, meta_key = _catalog_artifact_keys(settings)
    vectors_key = _vectors_key(settings)

    for rec in records:
        s3 = (rec.get("s3") or {}).get("object") or {}
        bucket = ((rec.get("s3") or {}).get("bucket") or {}).get("name") or settings.s3_bucket
        key = s3.get("key")
        if not key:
            continue

        job_id = os.path.basename(key)
        store.set_status(job_id=job_id, status="PROCESSING")

        try:
            image_bytes = get_object_bytes(bucket=bucket, key=key)

            tmp = Path("/tmp")
            index_path = tmp / "index.faiss"
            meta_path = tmp / "metadata.json"
            vectors_path = tmp / "vectors.npy"

            if not index_path.exists():
                download_to_path(bucket=settings.s3_bucket, key=index_key, dest_path=str(index_path))
            if not meta_path.exists():
                download_to_path(bucket=settings.s3_bucket, key=meta_key, dest_path=str(meta_path))
            if not vectors_path.exists():
                download_to_path(bucket=settings.s3_bucket, key=vectors_key, dest_path=str(vectors_path))

            from app.vision.embeddings import embed_image_bytes

            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)

            q = embed_image_bytes(image_bytes, model=settings.embedding_model).astype("float32")

            idxs = None
            scores = None
            try:
                from app.search.index import load_faiss_index, search_top_k

                index = load_faiss_index(str(index_path))
                idxs, scores = search_top_k(index=index, query_vec=q, k=5)
            except Exception:  # noqa: BLE001
                X = np.load(str(vectors_path)).astype("float32")
                s = X @ q
                idxs = np.argsort(-s)[:5]
                scores = s[idxs]

            results: list[dict] = []
            for i, s in zip(list(idxs), list(scores), strict=False):
                item = dict(meta[int(i)])
                item["score"] = float(s)
                results.append(item)

            store.set_results(job_id=job_id, status="DONE", results=results)
        except Exception:  # noqa: BLE001
            store.set_results(job_id=job_id, status="ERROR", results=[])
