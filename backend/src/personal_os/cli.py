from __future__ import annotations

import argparse
import json

from personal_os.adapters.persistence.database import (
    assert_postgresql_schema_current,
    create_database_engine,
)
from personal_os.adapters.persistence.repositories import create_uow_factory
from personal_os.application.commands import RecoverOutboxEventCommand
from personal_os.config import Settings
from personal_os.fixtures import load_synthetic_fixtures
from personal_os.worker import OutboxProcessor


def main() -> None:
    parser = argparse.ArgumentParser(description="PERSONAL OS local utility")
    parser.add_argument(
        "command",
        choices=[
            "fixtures-load",
            "outbox-run-once",
            "outbox-list-failed",
            "outbox-recover",
        ],
    )
    parser.add_argument("--event-id")
    parser.add_argument("--reason")
    parser.add_argument("--correlation-id")
    parser.add_argument("--idempotency-key")
    args = parser.parse_args()
    settings = Settings.from_environment()
    settings.validate_foundation_mode()
    engine = create_database_engine(settings.database_url)
    assert_postgresql_schema_current(engine)
    uow_factory = create_uow_factory(engine)
    if args.command == "fixtures-load":
        identifiers = load_synthetic_fixtures(uow_factory)
        print(f"Synthetic fixtures ready: {identifiers}")
        return
    processor = OutboxProcessor(
        uow_factory=uow_factory,
        environment=("test" if settings.environment == "test" else "development"),
    )
    if args.command == "outbox-run-once":
        result = processor.process_one()
        print(
            json.dumps(
                {
                    "event_id": result.event_id,
                    "failure_code": result.failure_code,
                    "status": result.status,
                },
                sort_keys=True,
            )
        )
        return
    if args.command == "outbox-list-failed":
        events = processor.failed_for_owner(
            actor_id=settings.development_user_id,
            owner_user_id=settings.development_user_id,
        )
        print(
            json.dumps(
                [
                    {
                        "attempt_count": event.attempt_count,
                        "cycle": event.cycle,
                        "event_id": event.id,
                        "event_type": event.event_type.value,
                        "failure_code": event.last_failure_code,
                        "status": event.status.value,
                    }
                    for event in events
                ],
                sort_keys=True,
            )
        )
        return
    if not all((args.event_id, args.reason, args.correlation_id, args.idempotency_key)):
        parser.error(
            "outbox-recover requires --event-id, --reason, --correlation-id, and --idempotency-key"
        )
    recovered = processor.recover_failed(
        RecoverOutboxEventCommand(
            user_id=settings.development_user_id,
            event_id=args.event_id,
            reason=args.reason,
            correlation_id=args.correlation_id,
            idempotency_key=args.idempotency_key,
        )
    )
    print(
        json.dumps(
            {
                "cycle": recovered.cycle,
                "event_id": recovered.id,
                "status": recovered.status.value,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
