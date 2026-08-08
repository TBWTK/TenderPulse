from __future__ import annotations

import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config

from tenderpulse.bootstrap import seed_demo
from tenderpulse.persistence.repository import ProcurementRepository
from tenderpulse.runtime import create_database, create_raw_store, utc_now
from tenderpulse.settings import Settings


def _alembic_config(database_url: str) -> Config:
    root = _project_root()
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def _project_root() -> Path:
    candidates = (Path.cwd(), *Path(__file__).resolve().parents)
    for candidate in candidates:
        if (candidate / "alembic.ini").is_file() and (candidate / "migrations").is_dir():
            return candidate
    raise RuntimeError("cannot locate alembic.ini and migrations directory")


def init_db(settings: Settings) -> None:
    command.upgrade(_alembic_config(settings.database_url), "head")
    _, factory = create_database(settings)
    with factory.begin() as session:
        ProcurementRepository(session).backfill_organization_links(at=utc_now())


def seed(settings: Settings) -> None:
    _, factory = create_database(settings)
    result = seed_demo(factory, create_raw_store(settings), now=utc_now)
    print(f"demo seed complete: runs={result.run_count} records={result.record_count}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="tenderpulse")
    parser.add_argument("command", choices=("init-db", "seed-demo", "init-and-seed"))
    args = parser.parse_args()
    settings = Settings()
    if args.command in {"init-db", "init-and-seed"}:
        init_db(settings)
    if args.command in {"seed-demo", "init-and-seed"}:
        seed(settings)


if __name__ == "__main__":
    main()
