from __future__ import annotations

import uuid
from pathlib import Path
import subprocess
import sys
import os

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.aws.s3 import presign_get_url, presign_put_url
from app.config import get_settings
from app.models import ResultsResponse, UploadUrlResponse
from app.store.jobs import DynamoJobsStore, LocalJobsStore


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _project_root() -> Path:
    # /TrendLens/api/app/main.py -> parents[2] == /TrendLens
    return Path(__file__).resolve().parents[2]


def _api_root() -> Path:
    # /TrendLens/api/app/main.py -> parents[1] == /TrendLens/api
    return Path(__file__).resolve().parents[1]


def _get_store():
    settings = get_settings()
    if settings.app_env == "aws":
        if not settings.ddb_table:
            raise RuntimeError("DDB_TABLE is required in aws mode")
        return DynamoJobsStore(settings.ddb_table)
    return LocalJobsStore(settings.local_root)


@app.post("/upload-url", response_model=UploadUrlResponse)
def create_upload_url(request: Request):
    settings = get_settings()
    store = _get_store()

    job_id = uuid.uuid4().hex[:12]

    if settings.app_env == "aws":
        if not settings.s3_bucket:
            raise HTTPException(status_code=500, detail="S3_BUCKET is required")
        object_key = f"{settings.uploads_prefix}{job_id}"
        store.create_job(job_id=job_id, object_key=object_key)
        upload_url = presign_put_url(bucket=settings.s3_bucket, key=object_key, expires_in=600)
        return UploadUrlResponse(jobId=job_id, uploadUrl=upload_url, objectKey=object_key)

    object_key = f"local/{job_id}"
    store.create_job(job_id=job_id, object_key=object_key)
    base = str(request.base_url).rstrip("/")
    upload_url = f"{base}/local-upload/{job_id}"
    return UploadUrlResponse(jobId=job_id, uploadUrl=upload_url, objectKey=object_key)


@app.put("/local-upload/{job_id}")
async def local_upload(job_id: str, request: Request):
    settings = get_settings()
    if settings.app_env == "aws":
        raise HTTPException(status_code=400, detail="local upload not available in aws mode")

    store = _get_store()
    job = store.get_job(job_id=job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="empty body")

    try:
        local_store: LocalJobsStore = store  # type: ignore[assignment]
        local_store.save_upload_bytes(job_id=job_id, content=content)
        store.set_status(job_id=job_id, status="PROCESSING")

        # IMPORTANT: torch/faiss can crash the interpreter on some macOS setups.
        # Run heavy processing in a subprocess so the API stays alive.
        api_root = _api_root()
        python = sys.executable
        if not os.path.exists(python):
            candidate = api_root / ".venv" / "bin" / "python"
            if candidate.exists():
                python = str(candidate)

        logs_dir = os.path.join(os.path.abspath(settings.local_root), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_path = os.path.join(logs_dir, f"{job_id}.log")
        logf = open(log_path, "ab", buffering=0)
        try:
            subprocess.Popen(
                [python, "-m", "app.worker.local_runner", "--job-id", job_id],
                cwd=str(api_root),
                stdout=logf,
                stderr=logf,
                start_new_session=True,
            )
        finally:
            logf.close()
    except Exception as exc:  # noqa: BLE001
        store.set_results(job_id=job_id, status="ERROR", results=[])
        raise HTTPException(status_code=500, detail=str(exc))

    return Response(status_code=200)


@app.get("/results/{job_id}", response_model=ResultsResponse)
def get_results(job_id: str, request: Request):
    settings = get_settings()
    store = _get_store()

    job = store.get_job(job_id=job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    results = job.results
    if settings.app_env == "aws" and settings.s3_bucket:
        enriched: list[dict] = []
        for item in results or []:
            image_key = item.get("image_key")
            if image_key:
                item = dict(item)
                item["image_url"] = presign_get_url(bucket=settings.s3_bucket, key=image_key)
            enriched.append(item)
        results = enriched
    else:
        base = str(request.base_url).rstrip("/")
        enriched = []
        for item in results or []:
            image_filename = item.get("image_filename")
            if image_filename:
                item = dict(item)
                item["image_url"] = f"{base}/catalog-image/{image_filename}"
            enriched.append(item)
        results = enriched

    return ResultsResponse(jobId=job.jobId, status=job.status, results=results)


@app.get("/catalog-image/{image_filename}")
def catalog_image(image_filename: str):
    settings = get_settings()
    if settings.app_env == "aws":
        raise HTTPException(status_code=404, detail="not available")

    images_dir = _project_root() / "catalog" / "images"
    path = images_dir / image_filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(str(path))
