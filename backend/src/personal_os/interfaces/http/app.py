from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Engine

from personal_os.adapters.persistence.database import (
    assert_postgresql_schema_current,
    create_database_engine,
    initialize_schema,
)
from personal_os.adapters.persistence.repositories import create_uow_factory
from personal_os.adapters.providers.mock import (
    DeterministicMockCalendarProvider,
    DeterministicMockModelProvider,
)
from personal_os.application.commands import (
    CaptureIntentCommand,
    DecideProposalCommand,
    ProposalDecision,
    RecoverOutboxEventCommand,
)
from personal_os.application.queries import DashboardQuery
from personal_os.application.services import PersonalOSService
from personal_os.capabilities import CAPABILITIES
from personal_os.config import Settings
from personal_os.domain.errors import (
    AuthorizationError,
    ConflictError,
    DomainError,
    InvalidTransitionError,
    NotFoundError,
    ProhibitedCapabilityError,
    ValidationError,
)
from personal_os.domain.events import OutboxStatus
from personal_os.fixtures import load_synthetic_fixtures
from personal_os.interfaces.http.schemas import (
    CaptureRequest,
    CaptureResponse,
    DashboardResponse,
    DecisionRequest,
    DecisionResponse,
    ExecutionEventView,
    ExecutionRecoveryRequest,
    commitment_view,
    intent_view,
    proposal_view,
)
from personal_os.observability import configure_logging
from personal_os.worker import OutboxProcessor


def create_app(settings: Settings | None = None, engine: Engine | None = None) -> FastAPI:
    current_settings = settings or Settings.from_environment()
    current_settings.validate_foundation_mode()
    database_engine = engine or create_database_engine(current_settings.database_url)
    api_logger = configure_logging()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        if current_settings.auto_initialize:
            initialize_schema(database_engine)
        else:
            assert_postgresql_schema_current(database_engine)
        uow_factory = create_uow_factory(database_engine)
        if current_settings.auto_initialize:
            load_synthetic_fixtures(uow_factory)
        application.state.uow_factory = uow_factory
        application.state.service = PersonalOSService(
            uow_factory=uow_factory,
            model_provider=DeterministicMockModelProvider(),
            calendar_provider=DeterministicMockCalendarProvider(),
        )
        application.state.dashboard = DashboardQuery(
            uow_factory, provider_mode=current_settings.provider_mode
        )
        application.state.outbox_processor = OutboxProcessor(
            uow_factory=uow_factory,
            environment=("test" if current_settings.environment == "test" else "development"),
        )
        yield

    application = FastAPI(
        title="PERSONAL OS",
        version="0.1.0",
        description="Foundation v0.1 local, synthetic, mock-only API",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Idempotency-Key", "If-Match", "X-Correlation-ID"],
    )

    @application.middleware("http")
    async def secure_local_responses(request: Request, call_next: Any) -> Any:
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id or len(correlation_id) > 64 or not correlation_id.isascii():
            correlation_id = str(uuid4())
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        if request.url.path.startswith("/v1/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Personal-OS-Mode"] = (
                f"local-{current_settings.provider_mode}-synthetic"
            )
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Correlation-ID"] = correlation_id
        route = request.scope.get("route")
        route_template = getattr(route, "path", "unmatched")
        api_logger.info(
            "http_request_completed",
            extra={
                "event_fields": {
                    "method": request.method,
                    "route": route_template,
                    "status": response.status_code,
                    "correlation_id": correlation_id,
                    "provider_mode": current_settings.provider_mode,
                }
            },
        )
        return response

    @application.exception_handler(DomainError)
    async def domain_problem(request: Request, exc: DomainError) -> JSONResponse:
        status = 422
        if isinstance(exc, (AuthorizationError, NotFoundError)):
            status = 404
        elif isinstance(exc, (ConflictError, InvalidTransitionError)):
            status = 409
        elif isinstance(exc, ProhibitedCapabilityError):
            status = 403
        elif isinstance(exc, ValidationError):
            status = 422
        instance = (
            "/v1/protected-resource" if isinstance(exc, AuthorizationError) else request.url.path
        )
        return JSONResponse(
            status_code=status,
            content={
                "type": f"https://personal-os.local/problems/{exc.code}",
                "title": exc.code.replace("_", " ").title(),
                "status": status,
                "detail": str(exc),
                "instance": str(instance),
            },
            media_type="application/problem+json",
        )

    def actor_id() -> str:
        # Deliberately server-derived. Client-supplied user/household/role fields are ignored.
        return current_settings.development_user_id

    @application.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "mode": f"local-{current_settings.provider_mode}-synthetic",
        }

    @application.get("/v1/system/capabilities")
    def capabilities() -> dict[str, object]:
        return {
            "phase": "foundation-v0.1",
            "accepted_capability_baseline": "foundation-v0.1",
            "engineering_phase": "foundation-v0.2-persistence-execution",
            "live_capabilities": [],
            "capabilities": CAPABILITIES,
        }

    @application.get("/v1/system/status")
    def system_status() -> dict[str, object]:
        return {
            "environment": "LOCAL",
            "provider_mode": current_settings.provider_mode.upper(),
            "data_mode": "SYNTHETIC",
            "identity_mode": "DEVELOPMENT PERSONA",
            "external_actions": "PROHIBITED",
        }

    @application.get("/v1/execution/status")
    def execution_status(request: Request) -> dict[str, object]:
        processor: OutboxProcessor = request.app.state.outbox_processor
        counts = processor.status_for_owner(actor_id=actor_id(), owner_user_id=actor_id())
        return {
            "mode": "LOCAL INTERNAL ONLY",
            "external_actions": "PROHIBITED",
            "counts": {status.value: counts[status] for status in OutboxStatus},
        }

    @application.get("/v1/execution/failed", response_model=list[ExecutionEventView])
    def failed_execution(request: Request) -> list[ExecutionEventView]:
        processor: OutboxProcessor = request.app.state.outbox_processor
        return [
            ExecutionEventView(
                id=event.id,
                event_type=event.event_type.value,
                status=event.status.value,
                attempt_count=event.attempt_count,
                max_attempts=event.max_attempts,
                cycle=event.cycle,
                last_failure_code=event.last_failure_code,
                occurred_at=event.occurred_at,
            )
            for event in processor.failed_for_owner(actor_id=actor_id(), owner_user_id=actor_id())
        ]

    @application.post(
        "/v1/execution/{event_id}/recover",
        response_model=ExecutionEventView,
    )
    def recover_execution(
        event_id: str,
        body: ExecutionRecoveryRequest,
        request: Request,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    ) -> ExecutionEventView:
        processor: OutboxProcessor = request.app.state.outbox_processor
        event = processor.recover_failed(
            RecoverOutboxEventCommand(
                user_id=actor_id(),
                event_id=event_id,
                reason=body.reason,
                correlation_id=request.state.correlation_id,
                idempotency_key=idempotency_key,
            )
        )
        return ExecutionEventView(
            id=event.id,
            event_type=event.event_type.value,
            status=event.status.value,
            attempt_count=event.attempt_count,
            max_attempts=event.max_attempts,
            cycle=event.cycle,
            last_failure_code=event.last_failure_code,
            occurred_at=event.occurred_at,
        )

    @application.post("/v1/intents", response_model=CaptureResponse, status_code=201)
    def capture_intent(
        body: CaptureRequest,
        request: Request,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    ) -> CaptureResponse:
        service: PersonalOSService = request.app.state.service
        result = service.capture_intent(
            CaptureIntentCommand(
                user_id=actor_id(),
                raw_text=body.text,
                correlation_id=request.state.correlation_id,
                idempotency_key=idempotency_key,
            )
        )
        return CaptureResponse(
            intent=intent_view(result.intent),
            commitment=commitment_view(result.commitment),
            proposal=proposal_view(result.proposal),
        )

    @application.post(
        "/v1/schedule-proposals/{proposal_id}/decisions",
        response_model=DecisionResponse,
    )
    def decide_proposal(
        proposal_id: str,
        body: DecisionRequest,
        request: Request,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
        if_match: str = Header(alias="If-Match"),
    ) -> DecisionResponse:
        try:
            expected_version = int(if_match.strip('"'))
        except ValueError as exc:
            raise ValidationError("If-Match must contain an integer proposal version") from exc
        service: PersonalOSService = request.app.state.service
        result = service.decide_proposal(
            DecideProposalCommand(
                user_id=actor_id(),
                proposal_id=proposal_id,
                decision=ProposalDecision(body.decision),
                expected_version=expected_version,
                correlation_id=request.state.correlation_id,
                idempotency_key=idempotency_key,
                requested_start=body.requested_start,
            )
        )
        commitment = commitment_view(result.commitment)
        if commitment is None:  # pragma: no cover - type-narrowing guard
            raise RuntimeError("decision result must include a commitment")
        proposal = proposal_view(result.proposal)
        if proposal is None:  # pragma: no cover - type-narrowing guard
            raise RuntimeError("decision result must include a proposal")
        return DecisionResponse(
            proposal=proposal,
            replacement=proposal_view(result.replacement),
            commitment=commitment,
        )

    @application.get("/v1/dashboard", response_model=DashboardResponse)
    def dashboard(request: Request) -> dict[str, Any]:
        query: DashboardQuery = request.app.state.dashboard
        return query.load(actor_id())

    @application.get("/v1/finance/transactions")
    def finance_transactions(request: Request) -> list[dict[str, Any]]:
        query: DashboardQuery = request.app.state.dashboard
        return query.load(actor_id())["transactions"]

    @application.get("/v1/finance/transactions/{transaction_id}")
    def finance_transaction(transaction_id: str, request: Request) -> dict[str, Any]:
        query: DashboardQuery = request.app.state.dashboard
        return query.transaction(actor_id(), transaction_id)

    @application.get("/v1/audit-events")
    def audit_events(request: Request) -> list[dict[str, Any]]:
        query: DashboardQuery = request.app.state.dashboard
        return query.load(actor_id())["activity"]

    frontend_dist = Path(__file__).resolve().parents[5] / "frontend" / "dist"
    if frontend_dist.exists():
        application.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

    return application


app = create_app()
