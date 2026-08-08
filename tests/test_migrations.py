from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from tenderpulse.cli import init_db
from tenderpulse.settings import Settings


def test_initial_migration_creates_lineage_schema(tmp_path: Path) -> None:
    path = tmp_path / "migration.sqlite"
    database_url = f"sqlite+pysqlite:///{path}"

    init_db(Settings(database_url=database_url))

    engine = create_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    assert {
        "alembic_version",
        "ai_extraction_attempts",
        "alert_delivery_attempts",
        "alert_events",
        "company_profiles",
        "ingestion_runs",
        "organization_aliases",
        "organizations",
        "procurement_organization_links",
        "procurement_records",
        "procurement_versions",
        "raw_artifacts",
    } <= tables
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "0006_ai_evidence_coverage"
        )
