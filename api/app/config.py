from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_env: str

    # Local mode
    local_root: str

    # AWS mode
    s3_bucket: str | None
    uploads_prefix: str
    catalog_prefix: str

    ddb_table: str | None

    embedding_model: str


def get_settings() -> Settings:
    app_env = os.getenv("APP_ENV", "local")

    return Settings(
        app_env=app_env,
        local_root=os.getenv("LOCAL_ROOT", os.path.join(os.path.dirname(__file__), "..", ".local")),
        s3_bucket=os.getenv("S3_BUCKET"),
        uploads_prefix=os.getenv("UPLOADS_PREFIX", "uploads/"),
        catalog_prefix=os.getenv("CATALOG_PREFIX", "catalog/"),
        ddb_table=os.getenv("DDB_TABLE"),

        # Embeddings
        embedding_model=os.getenv("EMBEDDING_MODEL", "resnet50"),
    )
