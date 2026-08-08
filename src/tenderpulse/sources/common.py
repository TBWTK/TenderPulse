from __future__ import annotations

import hashlib

DEFAULT_SOURCE_RECORDS = 100
MAX_SOURCE_RECORDS = 500


class SourceContractError(ValueError):
    """The source response or requested scope violates a declared adapter contract."""


def raw_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()
