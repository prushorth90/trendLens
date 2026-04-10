from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

from app.aws.ddb import table as ddb_table


def _now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class Job:
    jobId: str
    status: str
    objectKey: str
    results: list[dict]


class JobsStore:
    def create_job(self, *, job_id: str, object_key: str) -> None:
        raise NotImplementedError

    def set_status(self, *, job_id: str, status: str) -> None:
        raise NotImplementedError

    def set_results(self, *, job_id: str, status: str, results: list[dict]) -> None:
        raise NotImplementedError

    def get_job(self, *, job_id: str) -> Job | None:
        raise NotImplementedError


class LocalJobsStore(JobsStore):
    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        self.jobs_dir = os.path.join(self.root, "jobs")
        self.uploads_dir = os.path.join(self.root, "uploads")
        os.makedirs(self.jobs_dir, exist_ok=True)
        os.makedirs(self.uploads_dir, exist_ok=True)

    def _job_path(self, job_id: str) -> str:
        return os.path.join(self.jobs_dir, f"{job_id}.json")

    def create_job(self, *, job_id: str, object_key: str) -> None:
        job = {
            "jobId": job_id,
            "status": "PENDING",
            "objectKey": object_key,
            "results": [],
            "createdAt": _now_ms(),
            "updatedAt": _now_ms(),
        }
        with open(self._job_path(job_id), "w", encoding="utf-8") as f:
            json.dump(job, f)

    def set_status(self, *, job_id: str, status: str) -> None:
        path = self._job_path(job_id)
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            job = json.load(f)
        job["status"] = status
        job["updatedAt"] = _now_ms()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(job, f)

    def set_results(self, *, job_id: str, status: str, results: list[dict]) -> None:
        path = self._job_path(job_id)
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            job = json.load(f)
        job["status"] = status
        job["results"] = results
        job["updatedAt"] = _now_ms()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(job, f)

    def get_job(self, *, job_id: str) -> Job | None:
        path = self._job_path(job_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Job(
            jobId=data["jobId"],
            status=data.get("status", ""),
            objectKey=data.get("objectKey", ""),
            results=data.get("results", []),
        )

    def save_upload_bytes(self, *, job_id: str, content: bytes) -> str:
        path = os.path.join(self.uploads_dir, f"{job_id}.bin")
        with open(path, "wb") as f:
            f.write(content)
        return path


class DynamoJobsStore(JobsStore):
    def __init__(self, table_name: str):
        self.table = ddb_table(table_name)

    def create_job(self, *, job_id: str, object_key: str) -> None:
        self.table.put_item(
            Item={
                "jobId": job_id,
                "status": "PENDING",
                "objectKey": object_key,
                "results": [],
                "createdAt": _now_ms(),
                "updatedAt": _now_ms(),
            }
        )

    def set_status(self, *, job_id: str, status: str) -> None:
        self.table.update_item(
            Key={"jobId": job_id},
            UpdateExpression="SET #s = :s, updatedAt = :u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": status, ":u": _now_ms()},
        )

    def set_results(self, *, job_id: str, status: str, results: list[dict]) -> None:
        self.table.update_item(
            Key={"jobId": job_id},
            UpdateExpression="SET #s = :s, results = :r, updatedAt = :u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": status, ":r": results, ":u": _now_ms()},
        )

    def get_job(self, *, job_id: str) -> Job | None:
        resp = self.table.get_item(Key={"jobId": job_id})
        item: dict[str, Any] | None = resp.get("Item")
        if not item:
            return None
        return Job(
            jobId=item["jobId"],
            status=item.get("status", ""),
            objectKey=item.get("objectKey", ""),
            results=item.get("results", []),
        )
