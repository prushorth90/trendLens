from __future__ import annotations

import boto3


def s3_client():
    return boto3.client("s3")


def presign_put_url(*, bucket: str, key: str, expires_in: int = 600) -> str:
    client = s3_client()
    return client.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )


def presign_get_url(*, bucket: str, key: str, expires_in: int = 3600) -> str:
    client = s3_client()
    return client.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )


def download_to_path(*, bucket: str, key: str, dest_path: str) -> None:
    client = s3_client()
    client.download_file(bucket, key, dest_path)


def get_object_bytes(*, bucket: str, key: str) -> bytes:
    client = s3_client()
    resp = client.get_object(Bucket=bucket, Key=key)
    return resp["Body"].read()
