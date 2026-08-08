from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from tenderpulse.ai.gigachat import GigaChatClient, GigaChatError, GigaChatProtocolError


def test_gigachat_uses_oauth_cache_and_forced_function_call() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/v2/oauth":
            assert request.headers["Authorization"] == "Basic auth-key"
            assert request.headers["RqUID"]
            assert request.content == b"scope=GIGACHAT_API_PERS"
            return httpx.Response(
                200,
                json={"access_token": "access-token", "expires_at": 4_102_444_800_000},
            )
        assert request.url == httpx.URL("https://api.giga.chat/v1/chat/completions")
        assert request.headers["Authorization"] == "Bearer access-token"
        body = json.loads(request.content)
        assert body["function_call"] == {"name": "extract_tender_evidence"}
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "function_call",
                        "message": {
                            "function_call": {
                                "name": "extract_tender_evidence",
                                "arguments": {
                                    "requirements_status": "unknown",
                                    "requirements": [],
                                    "deadlines_status": "unknown",
                                    "deadlines": [],
                                    "gaps": ["No requirements found."],
                                },
                            }
                        },
                    }
                ],
                "model": "GigaChat-2:fixture",
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = GigaChatClient(
        authorization_key=SecretStr("auth-key"),
        scope="GIGACHAT_API_PERS",
        ca_bundle_file=Path("certs/russian_trusted_root_ca_pem.crt"),
        http_client=http_client,
    )

    first = client.extract_arguments("record evidence")
    second = client.extract_arguments("record evidence")

    assert first.arguments["gaps"] == ["No requirements found."]
    assert first.response_model == "GigaChat-2:fixture"
    assert second == first
    assert [request.url.path for request in requests].count("/api/v2/oauth") == 1


def test_gigachat_marks_rate_limit_as_retryable_without_leaking_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/oauth":
            return httpx.Response(429, text="secret upstream body")
        raise AssertionError("chat endpoint must not be called")

    client = GigaChatClient(
        authorization_key=SecretStr("auth-key"),
        scope="GIGACHAT_API_PERS",
        ca_bundle_file=Path("certs/russian_trusted_root_ca_pem.crt"),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(GigaChatError) as captured:
        client.extract_arguments("record evidence")

    assert captured.value.code == "gigachat_oauth_429"
    assert captured.value.retryable is True
    assert "secret upstream body" not in str(captured.value)


def test_gigachat_rejects_non_function_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/oauth":
            return httpx.Response(
                200,
                json={"access_token": "access-token", "expires_at": 4_102_444_800_000},
            )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": "unstructured answer"},
                    }
                ],
                "model": "GigaChat-2:fixture",
            },
        )

    client = GigaChatClient(
        authorization_key=SecretStr("auth-key"),
        scope="GIGACHAT_API_PERS",
        ca_bundle_file=Path("certs/russian_trusted_root_ca_pem.crt"),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(GigaChatProtocolError, match="forced function call"):
        client.extract_arguments("record evidence")
