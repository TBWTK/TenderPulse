from __future__ import annotations

from typing import Any

import pytest
from botocore.exceptions import ClientError

from tenderpulse.raw_store import S3RawStore


class FakeS3Client:
    def __init__(self) -> None:
        self.buckets: set[str] = set()
        self.objects: dict[tuple[str, str], dict[str, Any]] = {}
        self.put_count = 0

    def head_bucket(self, *, Bucket: str) -> None:
        if Bucket not in self.buckets:
            raise _not_found("HeadBucket")

    def create_bucket(self, *, Bucket: str) -> None:
        self.buckets.add(Bucket)

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        try:
            item = self.objects[(Bucket, Key)]
        except KeyError as exc:
            raise _not_found("HeadObject") from exc
        return {"ContentLength": len(item["Body"]), "Metadata": item["Metadata"]}

    def put_object(self, **kwargs: Any) -> None:
        self.put_count += 1
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs


def _not_found(operation: str) -> ClientError:
    return ClientError({"Error": {"Code": "404", "Message": "not found"}}, operation)


def test_s3_store_is_content_addressed_and_idempotent() -> None:
    client = FakeS3Client()
    store = S3RawStore(client, bucket="tenderpulse-raw")
    digest = "a" * 64
    store.ensure_bucket()

    first = store.put(
        source="ted",
        sha256=digest,
        content=b"payload",
        content_type="application/json",
    )
    replay = store.put(
        source="ted",
        sha256=digest,
        content=b"payload",
        content_type="application/json",
    )

    assert first == replay == f"s3://tenderpulse-raw/raw/ted/aa/{digest}"
    assert client.put_count == 1


def test_s3_store_fails_on_corrupt_existing_object() -> None:
    client = FakeS3Client()
    store = S3RawStore(client, bucket="tenderpulse-raw")
    digest = "b" * 64
    store.ensure_bucket()
    key = f"raw/ted/bb/{digest}"
    client.objects[("tenderpulse-raw", key)] = {"Body": b"different", "Metadata": {}}

    with pytest.raises(RuntimeError, match="corrupt"):
        store.put(
            source="ted",
            sha256=digest,
            content=b"payload",
            content_type="application/json",
        )
