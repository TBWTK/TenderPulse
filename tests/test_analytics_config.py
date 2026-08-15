import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_dbt_default_port_matches_compose_published_default() -> None:
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text()
    profile = (PROJECT_ROOT / "analytics" / "profiles.yml").read_text()

    compose_match = re.search(r"TENDERPULSE_DB_PORT:-(?P<port>\d+)", compose)
    dbt_match = re.search(r"env_var\('DBT_PORT', '(?P<port>\d+)'\)", profile)

    assert compose_match is not None
    assert dbt_match is not None
    assert dbt_match["port"] == compose_match["port"]


def test_dbt_current_product_staging_is_eis_russian_only_and_projects_geography() -> None:
    staging = (
        PROJECT_ROOT / "analytics" / "models" / "staging" / "stg_current_procurement_records.sql"
    ).read_text()

    assert "r.source = 'eis'" in staging
    assert "v.payload -> 'countries'" in staging
    assert "'RU'" in staging
    assert "region_codes" in staging
    assert "delivery_location" in staging
