from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tenderpulse.persistence.models import Base
from tenderpulse.persistence.repository import ProcurementRepository
from tenderpulse.profiles import load_demo_profiles
from tenderpulse.runtime import create_profile_provider


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
        repository.seed_profiles(load_demo_profiles())
    profiles = create_profile_provider(factory)

    assert next(item for item in profiles() if item.slug == "it-russia-integrator").version == 1

    with factory.begin() as session:
        repository = ProcurementRepository(session)
        current = repository.get_profile("it-russia-integrator")
        assert current is not None
        repository.add_profile_version(current.model_copy(update={"version": 2}))

    assert next(item for item in profiles() if item.slug == "it-russia-integrator").version == 2
