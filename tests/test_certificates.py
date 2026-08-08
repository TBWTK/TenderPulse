from __future__ import annotations

import hashlib
import ssl
from pathlib import Path

CERTS = Path(__file__).parents[1] / "certs"


def _fingerprint(path: Path) -> str:
    pem = path.read_text()
    der = ssl.PEM_cert_to_DER_cert(pem)
    return hashlib.sha256(der).hexdigest()


def test_pinned_russian_tls_chain_has_expected_public_fingerprints() -> None:
    assert _fingerprint(CERTS / "russian_trusted_root_ca_pem.crt") == (
        "d26d2d0231b7c39f92cc738512ba54103519e4405d68b5bd703e9788ca8ecf31"
    )
    assert _fingerprint(CERTS / "russian_trusted_sub_ca_pem.crt") == (
        "2155785036c900dbb5f1bb2a1569c80c55595bd6bf94867a29bbddbc7d88a3f2"
    )


def test_ssl_context_accepts_root_and_intermediate_files() -> None:
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=CERTS / "russian_trusted_root_ca_pem.crt")
    context.load_verify_locations(cafile=CERTS / "russian_trusted_sub_ca_pem.crt")
