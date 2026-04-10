from __future__ import annotations

import argparse
import traceback
import sys

from app.config import get_settings
from app.store.jobs import LocalJobsStore
from app.worker.process import process_image_bytes_local


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    args = parser.parse_args()

    settings = get_settings()
    store = LocalJobsStore(settings.local_root)

    try:
        upload_path = store.uploads_dir + f"/{args.job_id}.bin"
        with open(upload_path, "rb") as f:
            image_bytes = f.read()

        results = process_image_bytes_local(image_bytes=image_bytes)
        store.set_results(job_id=args.job_id, status="DONE", results=results)
    except Exception:  # noqa: BLE001
        traceback.print_exc(file=sys.stderr)
        store.set_results(job_id=args.job_id, status="ERROR", results=[])


if __name__ == "__main__":
    main()
