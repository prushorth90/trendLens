from __future__ import annotations

import io
from functools import lru_cache
import os

import numpy as np
from PIL import Image


@lru_cache(maxsize=1)
def _model_and_preprocess():
    import torch
    from torchvision.models import resnet50, ResNet50_Weights

    weights = ResNet50_Weights.DEFAULT
    model = resnet50(weights=weights)
    model.fc = torch.nn.Identity()
    model.eval()

    preprocess = weights.transforms()
    return model, preprocess


@lru_cache(maxsize=1)
def _clip_model_and_preprocess():
    import open_clip

    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32",
        pretrained="laion2b_s34b_b79k",
    )
    model.eval()
    return model, preprocess


def embed_image_bytes(image_bytes: bytes, *, model: str | None = None) -> np.ndarray:
    import torch

    selected = (model or os.getenv("EMBEDDING_MODEL", "resnet50")).lower()

    if selected in {"clip", "clip-vit-b-32", "vit-b-32"}:
        clip_model, preprocess = _clip_model_and_preprocess()

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        x = preprocess(image).unsqueeze(0)

        with torch.no_grad():
            feats = clip_model.encode_image(x)
    else:
        resnet_model, preprocess = _model_and_preprocess()

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        x = preprocess(image).unsqueeze(0)

        with torch.no_grad():
            feats = resnet_model(x)

    vec = feats.squeeze(0).cpu().numpy().astype("float32")
    norm = np.linalg.norm(vec) + 1e-12
    return vec / norm
