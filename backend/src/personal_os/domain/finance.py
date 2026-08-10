from __future__ import annotations

from dataclasses import dataclass

from personal_os.domain.entities import FinancialTransaction


@dataclass(frozen=True, slots=True)
class CategorisationResult:
    category: str
    rule_id: str
    confidence: float


class DeterministicTransactionCategoriser:
    """Small auditable ruleset for synthetic demonstration data."""

    def categorise(self, transaction: FinancialTransaction) -> CategorisationResult:
        searchable = f"{transaction.merchant} {transaction.memo}".casefold()
        if any(term in searchable for term in ("timber", "lumber", "builders merchant")):
            return CategorisationResult(
                category="House project · materials",
                rule_id="house-materials-keyword-v1",
                confidence=0.98,
            )
        if any(term in searchable for term in ("contractor", "electrician", "plumber")):
            return CategorisationResult(
                category="House project · contractor",
                rule_id="house-contractor-keyword-v1",
                confidence=0.92,
            )
        return CategorisationResult(
            category="Needs review",
            rule_id="no-deterministic-match-v1",
            confidence=0.35,
        )
