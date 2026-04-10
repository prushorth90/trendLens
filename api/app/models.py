from __future__ import annotations

from pydantic import BaseModel, Field


class UploadUrlResponse(BaseModel):
    jobId: str = Field(..., min_length=8)
    uploadUrl: str
    objectKey: str


class ResultsResponse(BaseModel):
    jobId: str
    status: str
    results: list[dict]
