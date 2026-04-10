from __future__ import annotations

import numpy as np


def load_faiss_index(path: str):
    import faiss  # type: ignore

    return faiss.read_index(path)


def search_top_k(*, index, query_vec: np.ndarray, k: int = 5) -> tuple[np.ndarray, np.ndarray]:
    q = query_vec.astype("float32").reshape(1, -1)
    scores, idxs = index.search(q, k)
    return idxs[0], scores[0]
