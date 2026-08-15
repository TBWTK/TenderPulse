from __future__ import annotations

from datetime import datetime

from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tenderpulse.auth import LocalAccountSeed, seed_local_accounts
from tenderpulse.persistence.models import Base
from tenderpulse.persistence.repository import ProcurementRepository
from tenderpulse.profiles import load_demo_profiles, load_mvp2_legacy_test_profiles
from tenderpulse.runtime import create_account_profile_provider, create_profile_provider


def test_profile_provider_reads_the_current_database_version_on_every_call() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory.begin() as session:
        repository = ProcurementRepository(session)
        repository.seed_profiles(load_mvp2_legacy_test_profiles())
    profiles = create_profile_provider(factory)

    assert next(item for item in profiles() if item.slug == "it-russia-integrator").version == 1

    with factory.begin() as session:
        repository = ProcurementRepository(session)
        current = repository.get_profile("it-russia-integrator")
        assert current is not None
        repository.add_profile_version(current.model_copy(update={"version": 2}))

    assert next(item for item in profiles() if item.slug == "it-russia-integrator").version == 2


def test_account_profile_provider_excludes_unbound_legacy_profiles() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory.begin() as session:
        repository = ProcurementRepository(session)
        repository.seed_profiles(load_demo_profiles())
        repository.seed_profiles(load_mvp2_legacy_test_profiles())
        seed_local_accounts(
            session,
            (
                LocalAccountSeed(
                    slug="cleaning-demo",
                    display_name="Чистая территория",
                    profile_slug="cleaning-moscow",
                    access_code=SecretStr("cleaning-code-1234567890-abcdefghijkl"),
                ),
                LocalAccountSeed(
                    slug="office-demo",
                    display_name="Офисное снабжение",
                    profile_slug="office-supply-moscow",
                    access_code=SecretStr("office-code-1234567890-abcdefghijklm"),
                ),
            ),
            pepper=SecretStr("runtime-test-pepper-1234567890-abcdef"),
            now=lambda: datetime(2026, 8, 16),
        )

    profiles = create_account_profile_provider(factory)

    assert tuple(profile.slug for profile in profiles()) == (
        "cleaning-moscow",
        "office-supply-moscow",
    )
