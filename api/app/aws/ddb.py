from __future__ import annotations

import boto3


def ddb_resource():
    return boto3.resource("dynamodb")


def table(name: str):
    return ddb_resource().Table(name)
