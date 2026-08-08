from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from pydantic import SecretStr

OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
API_BASE_URL = "https://api.giga.chat/v1"
FUNCTION_NAME = "extract_tender_evidence"


class GigaChatError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class GigaChatProtocolError(GigaChatError):
    def __init__(self, message: str) -> None:
        super().__init__("gigachat_protocol", message, retryable=False)


@dataclass(frozen=True)
class GeneratedArguments:
    arguments: dict[str, Any]
    response_model: str


class GigaChatClient:
    def __init__(
        self,
        *,
        authorization_key: SecretStr,
        scope: str,
        ca_bundle_file: Path,
        model: str = "GigaChat-2",
        oauth_url: str = OAUTH_URL,
        api_base_url: str = API_BASE_URL,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not scope:
            raise ValueError("GigaChat scope cannot be empty")
        if http_client is None and not ca_bundle_file.is_file():
            raise ValueError(f"GigaChat CA bundle does not exist: {ca_bundle_file}")
        self._authorization_key = authorization_key
        self._scope = scope
        self._model = model
        self._oauth_url = oauth_url
        self._chat_url = f"{api_base_url.rstrip('/')}/chat/completions"
        self._http = http_client or httpx.Client(
            verify=str(ca_bundle_file),
            timeout=httpx.Timeout(30.0, connect=10.0),
        )
        self._access_token: str | None = None
        self._expires_at_ms = 0

    def extract_arguments(self, evidence: str) -> GeneratedArguments:
        token = self._get_access_token()
        request = {
            "model": self._model,
            "temperature": 0.01,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Extract only facts supported by verbatim citations from evidence_fields. "
                        "Set each coverage status to found, not_present, or unknown. "
                        "Use gaps for absent or ambiguous information; never guess."
                    ),
                },
                {"role": "user", "content": evidence},
            ],
            "function_call": {"name": FUNCTION_NAME},
            "functions": [_extraction_function_schema()],
        }
        try:
            response = self._http.post(
                self._chat_url,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                json=request,
            )
        except httpx.HTTPError as error:
            raise GigaChatError(
                "gigachat_transport",
                "GigaChat chat transport failed",
                retryable=True,
            ) from error
        _raise_for_status(response, operation="chat")
        payload = _response_json(response)
        try:
            choice = payload["choices"][0]
            function_call = choice["message"]["function_call"]
            function_name = function_call["name"]
            arguments = function_call["arguments"]
            response_model = payload["model"]
        except (KeyError, IndexError, TypeError) as error:
            raise GigaChatProtocolError(
                "GigaChat did not return the forced function call"
            ) from error
        if choice.get("finish_reason") != "function_call" or function_name != FUNCTION_NAME:
            raise GigaChatProtocolError("GigaChat did not return the forced function call")
        if not isinstance(arguments, dict) or not isinstance(response_model, str):
            raise GigaChatProtocolError("GigaChat function arguments have an invalid shape")
        return GeneratedArguments(arguments=arguments, response_model=response_model)

    def _get_access_token(self) -> str:
        if (
            self._access_token is not None
            and int(time.time() * 1000) < self._expires_at_ms - 60_000
        ):
            return self._access_token
        key = self._authorization_key.get_secret_value()
        authorization = key if key.startswith("Basic ") else f"Basic {key}"
        try:
            response = self._http.post(
                self._oauth_url,
                headers={
                    "Accept": "application/json",
                    "Authorization": authorization,
                    "RqUID": str(uuid4()),
                },
                data={"scope": self._scope},
            )
        except httpx.HTTPError as error:
            raise GigaChatError(
                "gigachat_oauth_transport",
                "GigaChat OAuth transport failed",
                retryable=True,
            ) from error
        _raise_for_status(response, operation="oauth")
        payload = _response_json(response)
        token = payload.get("access_token")
        expires_at = payload.get("expires_at")
        if not isinstance(token, str) or not token or not isinstance(expires_at, int):
            raise GigaChatProtocolError("GigaChat OAuth response has an invalid shape")
        self._access_token = token
        self._expires_at_ms = expires_at
        return token


def _raise_for_status(response: httpx.Response, *, operation: str) -> None:
    if response.is_success:
        return
    status = response.status_code
    raise GigaChatError(
        f"gigachat_{operation}_{status}",
        f"GigaChat {operation} returned HTTP {status}",
        retryable=status == 429 or status >= 500,
    )


def _response_json(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as error:
        raise GigaChatProtocolError("GigaChat returned invalid JSON") from error
    if not isinstance(payload, dict):
        raise GigaChatProtocolError("GigaChat returned a non-object JSON response")
    return payload


def _extraction_function_schema() -> dict[str, Any]:
    citation = {
        "type": "object",
        "properties": {
            "field": {"type": "string", "description": "Exact evidence_fields key"},
            "quote": {"type": "string", "description": "Exact verbatim substring"},
        },
        "required": ["field", "quote"],
    }
    return {
        "name": FUNCTION_NAME,
        "description": "Returns traceable tender requirements, deadlines and visible gaps.",
        "parameters": {
            "type": "object",
            "properties": {
                "requirements_status": {
                    "type": "string",
                    "enum": ["found", "not_present", "unknown"],
                },
                "requirements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "mandatory": {"type": "boolean", "nullable": True},
                            "citation": citation,
                        },
                        "required": ["text", "mandatory", "citation"],
                    },
                },
                "deadlines_status": {
                    "type": "string",
                    "enum": ["found", "not_present", "unknown"],
                },
                "deadlines": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "value": {"type": "string"},
                            "normalized_at": {"type": "string", "nullable": True},
                            "citation": citation,
                        },
                        "required": ["label", "value", "normalized_at", "citation"],
                    },
                },
                "gaps": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "requirements_status",
                "requirements",
                "deadlines_status",
                "deadlines",
                "gaps",
            ],
        },
    }
