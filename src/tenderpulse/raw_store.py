from __future__ import annotations

from typing import Any, Protocol

from botocore.exceptions import ClientError  # type: ignore[import-untyped]


class RawStore(Protocol):
    def put(
        self,
        *,
        source: str,
        sha256: str,
        content: bytes,
        content_type: str,
    ) -> str: ...


class MemoryRawStore:
    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def put(
        self,
        *,
        source: str,
        sha256: str,
        content: bytes,
        content_type: str,
    ) -> str:
        existing = self._objects.get(sha256)
        if existing is not None and existing != content:
            raise RuntimeError("raw SHA-256 collision or corrupt object store")
        self._objects[sha256] = content
        return f"memory://raw/{source}/{sha256}"

    def get(self, sha256: str) -> bytes:
        return self._objects[sha256]


class S3RawStore:
    def __init__(self, client: Any, *, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError as exc:
            if not _is_not_found(exc):
                raise
            self._client.create_bucket(Bucket=self._bucket)

    def put(
        self,
        *,
        source: str,
        sha256: str,
        content: bytes,
        content_type: str,
    ) -> str:
        key = f"raw/{source}/{sha256[:2]}/{sha256}"
        try:
            existing = self._client.head_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if not _is_not_found(exc):
                raise
        else:
            metadata = existing.get("Metadata", {})
            if existing.get("ContentLength") != len(content) or metadata.get("sha256") != sha256:
                raise RuntimeError("existing content-addressed raw object is corrupt")
            return f"s3://{self._bucket}/{key}"

        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
            Metadata={"sha256": sha256, "source": source},
        )
        return f"s3://{self._bucket}/{key}"


def _is_not_found(exc: ClientError) -> bool:
    code = str(exc.response.get("Error", {}).get("Code", ""))
    return code in {"404", "NoSuchBucket", "NoSuchKey", "NotFound"}
