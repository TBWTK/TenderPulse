from __future__ import annotations

from tenderpulse.settings import Settings


def test_settings_keep_secrets_redacted() -> None:
    settings = Settings(
        s3_secret_key="local-secret",
        gigachat_api_key="gigachat-secret",
        gigachat_client_id="client-secret",
    )

    rendered = repr(settings)

    assert "local-secret" not in rendered
    assert "gigachat-secret" not in rendered
    assert "client-secret" not in rendered
    assert "**********" in rendered


def test_live_ingestion_settings_are_bounded() -> None:
    settings = Settings(
        source_record_limit=500,
        ted_lookback_days=90,
        eis_lookback_days=31,
        usa_lookback_days=731,
    )

    assert settings.source_record_limit == 500
    assert settings.eis_root_ca_file.name == "russian_trusted_root_ca_pem.crt"
    assert settings.eis_sub_ca_file.name == "russian_trusted_sub_ca_pem.crt"
