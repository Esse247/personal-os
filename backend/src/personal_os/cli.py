from __future__ import annotations

import argparse

from personal_os.adapters.persistence.database import create_database_engine
from personal_os.adapters.persistence.repositories import create_uow_factory
from personal_os.config import Settings
from personal_os.fixtures import load_synthetic_fixtures


def main() -> None:
    parser = argparse.ArgumentParser(description="PERSONAL OS local utility")
    parser.add_argument("command", choices=["fixtures-load"])
    args = parser.parse_args()
    settings = Settings.from_environment()
    settings.validate_foundation_mode()
    engine = create_database_engine(settings.database_url)
    if args.command == "fixtures-load":
        identifiers = load_synthetic_fixtures(create_uow_factory(engine))
        print(f"Synthetic fixtures ready: {identifiers}")


if __name__ == "__main__":
    main()
