from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from personal_os.application.policy import AuthContext, FoundationPolicy, ResourceRef
from personal_os.config import DEMO_HOUSEHOLD_ID, DEMO_USER_ID, OTHER_USER_ID
from personal_os.domain.entities import (
    AuditEvent,
    ClassificationStatus,
    FinancialTransaction,
    Project,
    TransactionClassification,
    WorldFact,
)
from personal_os.domain.finance import DeterministicTransactionCategoriser
from personal_os.domain.provenance import (
    ConfirmationStatus,
    Provenance,
    Sensitivity,
    SourceType,
)
from personal_os.ports.providers import BankingProvider, ProviderRequestContext
from personal_os.ports.repositories import UnitOfWork

UnitOfWorkFactory = Callable[[], UnitOfWork]

WEDDING_FACT_ID = "fact-wedding-synthetic-001"
HOUSE_PROJECT_ID = "project-house-synthetic-001"
TRANSACTION_ID = "transaction-house-synthetic-001"
OTHER_TRANSACTION_ID = "transaction-private-other-user-001"


def load_synthetic_fixtures(
    uow_factory: UnitOfWorkFactory,
    banking_provider: BankingProvider | None = None,
    policy: FoundationPolicy | None = None,
) -> dict[str, str]:
    now = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)
    wedding_at = datetime(2026, 9, 19, 14, 0, tzinfo=UTC)
    categoriser = DeterministicTransactionCategoriser()
    current_policy = policy or FoundationPolicy()

    with uow_factory() as uow:
        if uow.world_facts.find_confirmed_by_label(DEMO_USER_ID, "Wedding") is None:
            uow.world_facts.add(
                WorldFact(
                    id=WEDDING_FACT_ID,
                    user_id=DEMO_USER_ID,
                    fact_type="calendar_deadline",
                    label="Wedding",
                    occurs_at=wedding_at,
                    provenance=Provenance(
                        source_type=SourceType.USER_STATED,
                        source_identifier="synthetic-fixture:wedding-date-v1",
                        observed_at=now,
                        recorded_at=now,
                        confidence=1.0,
                        confirmation_status=ConfirmationStatus.CONFIRMED,
                        sensitivity=Sensitivity.PERSONAL,
                        actor_id=DEMO_USER_ID,
                        data_subject_id=DEMO_USER_ID,
                        controller_id=DEMO_USER_ID,
                        correlation_id="fixture-load-v1",
                        valid_from=wedding_at,
                    ),
                    created_at=now,
                )
            )

        if uow.projects.primary_for_user(DEMO_USER_ID) is None:
            uow.projects.add(
                Project(
                    id=HOUSE_PROJECT_ID,
                    user_id=DEMO_USER_ID,
                    name="Lantern House · kitchen shell",
                    status="active",
                    is_primary=True,
                    created_at=now,
                )
            )

        transaction = uow.transactions.get(TRANSACTION_ID)
        if transaction is None:
            if banking_provider is None:
                from personal_os.adapters.providers.mock import SyntheticBankingProvider

                banking_provider = SyntheticBankingProvider()
            current_policy.authorize(
                AuthContext(DEMO_USER_ID, "load deterministic synthetic finance fixture"),
                "provider.banking.transactions.read.synthetic.own",
                ResourceRef(
                    "provider_capability",
                    "banking.transactions.read.synthetic",
                    DEMO_USER_ID,
                    "financial",
                ),
            )
            banking_result = banking_provider.read_synthetic_transactions(
                user_id=DEMO_USER_ID,
                context=ProviderRequestContext(
                    actor_id="fixture-loader-system",
                    on_behalf_of_id=DEMO_USER_ID,
                    correlation_id="fixture-load-v1",
                    capability="banking.transactions.read.synthetic",
                    purpose="load deterministic synthetic finance fixture",
                    deadline_at=now + timedelta(seconds=30),
                    idempotency_key="fixture-load-v1:banking-read",
                    task_type="fixture_load",
                    risk="medium",
                    privacy="financial",
                ),
            )
            if (
                banking_result.capability_mode != "mocked"
                or banking_result.canonical_error is not None
                or len(banking_result.value) != 1
            ):
                raise RuntimeError("synthetic banking provider returned an invalid fixture")
            source_transaction = banking_result.value[0]
            amount_minor = source_transaction["amount_minor"]
            if not isinstance(amount_minor, int):
                raise RuntimeError("synthetic transaction amount must use integer minor units")
            transaction = FinancialTransaction(
                id=TRANSACTION_ID,
                user_id=DEMO_USER_ID,
                household_id=DEMO_HOUSEHOLD_ID,
                project_id=HOUSE_PROJECT_ID,
                merchant=str(source_transaction["merchant"]),
                memo="Timber delivery · synthetic fixture",
                amount_minor=amount_minor,
                currency=str(source_transaction["currency"]),
                posted_at=datetime(2026, 8, 8, 10, 20, tzinfo=UTC),
                provenance=Provenance(
                    source_type=SourceType.TOOL_OBSERVED,
                    source_identifier=str(source_transaction["source_id"]),
                    observed_at=now,
                    recorded_at=now,
                    confidence=1.0,
                    confirmation_status=ConfirmationStatus.CONFIRMED,
                    sensitivity=Sensitivity.FINANCIAL,
                    actor_id="synthetic-banking-v1",
                    data_subject_id=DEMO_USER_ID,
                    controller_id=DEMO_USER_ID,
                    correlation_id="fixture-load-v1",
                ),
                created_at=now,
            )
            uow.transactions.add(transaction)
            result = categoriser.categorise(transaction)
            classification = TransactionClassification(
                id="classification-house-synthetic-001",
                transaction_id=transaction.id,
                category=result.category,
                rule_id=result.rule_id,
                confidence=result.confidence,
                status=ClassificationStatus.CONFIRMED,
                provenance=Provenance(
                    source_type=SourceType.SYSTEM_INFERRED,
                    source_identifier=f"deterministic-rule:{result.rule_id}",
                    observed_at=now,
                    recorded_at=now,
                    confidence=result.confidence,
                    confirmation_status=ConfirmationStatus.CONFIRMED,
                    sensitivity=Sensitivity.FINANCIAL,
                    actor_id="deterministic-finance-categoriser",
                    data_subject_id=DEMO_USER_ID,
                    controller_id=DEMO_USER_ID,
                    correlation_id="fixture-load-v1",
                    input_references=(transaction.provenance.source_identifier,),
                ),
                created_at=now,
            )
            uow.classifications.add(classification)
            uow.audit.append(
                AuditEvent(
                    id="audit-transaction-imported-001",
                    user_id=DEMO_USER_ID,
                    action="finance.transaction_imported",
                    entity_type="financial_transaction",
                    entity_id=transaction.id,
                    correlation_id="fixture-load-v1",
                    occurred_at=now,
                    outcome="succeeded",
                    source_type=SourceType.TOOL_OBSERVED.value,
                    source_identifier=transaction.provenance.source_identifier,
                    actor_id="synthetic-banking-v1",
                    on_behalf_of_id=DEMO_USER_ID,
                    entity_version=1,
                    causation_id="fixture-load-v1:transaction-import",
                    policy_result="allowed:fixture-policy-v1",
                    capability_mode="local-mock-synthetic",
                    tool_reference="synthetic-banking-v1",
                    summary="Synthetic house-project transaction loaded from mock banking data.",
                    details={
                        "provider_mode": "mocked",
                        "source_id": "synthetic-bank-transaction-001",
                    },
                )
            )
            uow.audit.append(
                AuditEvent(
                    id="audit-transaction-categorised-001",
                    user_id=DEMO_USER_ID,
                    action="finance.transaction_categorised",
                    entity_type="transaction_classification",
                    entity_id=classification.id,
                    correlation_id="fixture-load-v1",
                    occurred_at=now,
                    outcome="succeeded",
                    source_type=SourceType.SYSTEM_INFERRED.value,
                    source_identifier=classification.provenance.source_identifier,
                    actor_id="deterministic-finance-categoriser",
                    on_behalf_of_id=DEMO_USER_ID,
                    entity_version=1,
                    causation_id="fixture-load-v1:transaction-classification",
                    policy_result="allowed:fixture-policy-v1",
                    capability_mode="local-mock-synthetic",
                    tool_reference="deterministic-finance-categoriser",
                    summary="Deterministic rule classified the synthetic transaction.",
                    details={"rule_id": result.rule_id, "confidence": result.confidence},
                )
            )

        if uow.transactions.get(OTHER_TRANSACTION_ID) is None:
            uow.transactions.add(
                FinancialTransaction(
                    id=OTHER_TRANSACTION_ID,
                    user_id=OTHER_USER_ID,
                    household_id=DEMO_HOUSEHOLD_ID,
                    project_id=None,
                    merchant="Private synthetic merchant",
                    memo="Private fixture for isolation testing",
                    amount_minor=-1999,
                    currency="GBP",
                    posted_at=datetime(2026, 8, 9, 11, 0, tzinfo=UTC),
                    provenance=Provenance(
                        source_type=SourceType.TOOL_OBSERVED,
                        source_identifier="synthetic-private-transaction-other-user",
                        observed_at=now,
                        recorded_at=now,
                        confidence=1.0,
                        confirmation_status=ConfirmationStatus.CONFIRMED,
                        sensitivity=Sensitivity.FINANCIAL,
                        actor_id="synthetic-banking-v1",
                        data_subject_id=OTHER_USER_ID,
                        controller_id=OTHER_USER_ID,
                        correlation_id="fixture-load-v1",
                    ),
                    created_at=now,
                )
            )

        uow.commit()

    return {
        "user_id": DEMO_USER_ID,
        "wedding_fact_id": WEDDING_FACT_ID,
        "project_id": HOUSE_PROJECT_ID,
        "transaction_id": TRANSACTION_ID,
    }
