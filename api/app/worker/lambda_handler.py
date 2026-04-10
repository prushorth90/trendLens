from __future__ import annotations

import os

from app.config import get_settings
from app.store.jobs import DynamoJobsStore
from app.worker.process import process_s3_event


def lambda_handler(event, context):  # noqa: ANN001
    settings = get_settings()
    if settings.app_env != "aws":
        raise RuntimeError("Worker can only run in aws mode")
    if not settings.ddb_table:
        raise RuntimeError("DDB_TABLE is required")

    store = DynamoJobsStore(settings.ddb_table)
    process_s3_event(event=event, store=store)
    return {"ok": True}
