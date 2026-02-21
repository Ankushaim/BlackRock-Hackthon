"""
Orchestrator endpoint that chains all pipeline steps in one shot:
  1. Parse raw expenses -> transactions (ceiling + remanent)
  2. Validate transactions (remove negatives, dupes, out-of-bounds)
  3. Apply temporal rules: q (override), p (extra), k (grouping)
  4. Calculate both NPS and Index Fund returns in one response
"""

import math

from fastapi import APIRouter

from app.core.financial import (
    INDEX_RATE,
    NPS_RATE,
    calculate_compound_interest,
    calculate_inflation_adjustment,
    calculate_tax_benefit,
    calculate_time,
    group_savings_by_k,
)
from app.core.temporal import apply_temporal_rules
from app.models.schemas import (
    CamelModel,
    Expense,
    InvalidTransaction,
    KPeriod,
    PPeriod,
    QPeriod,
    ReturnsResponse,
    Transaction,
)

router = APIRouter()


class CalculateRequest(CamelModel):
    age: int
    wage: float
    inflation: float
    q: list[QPeriod] = []
    p: list[PPeriod] = []
    k: list[KPeriod] = []
    expenses: list[Expense]


class PipelineStepSummary(CamelModel):
    parsed: int  # how many expenses were parsed
    valid: int  # how many passed validation
    filtered: int  # how many had temporal rules applied
    rejected: int  # total dropped along the way


class CalculateResponse(CamelModel):
    summary: PipelineStepSummary
    rejected_transactions: list[InvalidTransaction]
    nps: ReturnsResponse
    index_fund: ReturnsResponse


def _parse(expenses: list[Expense]) -> list[Transaction]:
    result = []
    for exp in expenses:
        amount = exp.amount
        if amount == 0:
            ceiling, remanent = 0.0, 0.0
        else:
            base = math.floor(amount / 100.0) * 100.0
            ceiling = base + 100.0
            remanent = ceiling - amount
        result.append(
            Transaction(
                date=exp.date, amount=amount, ceiling=ceiling, remanent=remanent
            )
        )
    return result


def _validate(
    transactions: list[Transaction],
) -> tuple[list[Transaction], list[InvalidTransaction]]:
    seen_dates: set[str] = set()
    valid, invalid = [], []
    for t in transactions:
        if t.amount < 0:
            invalid.append(
                InvalidTransaction(**t.model_dump(), message="Negative amount")
            )
        elif t.amount >= 500000:
            invalid.append(
                InvalidTransaction(**t.model_dump(), message="Exceeds max limit")
            )
        elif t.date in seen_dates:
            invalid.append(
                InvalidTransaction(**t.model_dump(), message="Duplicate date")
            )
        else:
            valid.append(t)
            seen_dates.add(t.date)
    return valid, invalid


def _apply_rules(
    transactions: list[Transaction],
    q: list[QPeriod],
    p: list[PPeriod],
    k: list[KPeriod],
) -> tuple[list[Transaction], list[InvalidTransaction]]:
    valid, invalid = [], []
    for t in transactions:
        updated, err = apply_temporal_rules(t, q, p, k)
        if err:
            invalid.append(InvalidTransaction(**t.model_dump(), message=err))
        else:
            valid.append(updated)
    return valid, invalid


def _compute_returns(
    transactions: list[Transaction],
    k: list[KPeriod],
    age: int,
    wage: float,
    inflation: float,
    is_nps: bool,
) -> ReturnsResponse:
    total_amount = sum(t.amount for t in transactions)
    total_ceiling = sum(t.ceiling for t in transactions)
    savings = group_savings_by_k(transactions, k)
    t_years = calculate_time(age)
    annual_wage = wage * 12

    for s in savings:
        if s.amount > 0:
            rate = NPS_RATE if is_nps else INDEX_RATE
            fv = calculate_compound_interest(s.amount, rate, t_years)
            real_fv = calculate_inflation_adjustment(fv, inflation, t_years)
            s.profits = round(real_fv - s.amount, 2)
            if is_nps:
                s.tax_benefit = round(calculate_tax_benefit(s.amount, annual_wage), 2)

    return ReturnsResponse(
        transactions_total_amount=round(total_amount, 2),
        transactions_total_ceiling=round(total_ceiling, 2),
        savings_by_dates=savings,
    )


@router.post("/calculate", response_model=CalculateResponse)
async def calculate(request: CalculateRequest):
    # Step 1: parse raw expenses
    parsed = _parse(request.expenses)

    # Step 2: validate
    valid_txns, invalid_from_validation = _validate(parsed)

    # Step 3: apply temporal rules (q, p, k)
    filtered_txns, invalid_from_filter = _apply_rules(
        valid_txns, request.q, request.p, request.k
    )

    all_rejected = invalid_from_validation + invalid_from_filter

    # Step 4: calculate returns for both instruments in parallel
    nps_result = _compute_returns(
        filtered_txns,
        request.k,
        request.age,
        request.wage,
        request.inflation,
        is_nps=True,
    )
    index_result = _compute_returns(
        filtered_txns,
        request.k,
        request.age,
        request.wage,
        request.inflation,
        is_nps=False,
    )

    return CalculateResponse(
        summary=PipelineStepSummary(
            parsed=len(parsed),
            valid=len(valid_txns),
            filtered=len(filtered_txns),
            rejected=len(all_rejected),
        ),
        rejected_transactions=all_rejected,
        nps=nps_result,
        index_fund=index_result,
    )
