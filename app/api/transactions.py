import math

from fastapi import APIRouter

from app.core.temporal import apply_temporal_rules
from app.models.schemas import (
    Expense,
    FilterRequest,
    InvalidTransaction,
    Transaction,
    ValidationRequest,
    ValidationResponse,
)

router = APIRouter()


@router.post("/transactions:parse", response_model=list[Transaction])
async def parse_transactions(expenses: list[Expense]):
    result = []
    for exp in expenses:
        amount = exp.amount
        # get remnant by rounding to next 100
        # e.g., 250 -> 300, diff 50
        if amount == 0:
            ceiling, remanent = 0.0, 0.0
        else:
            base = math.floor(amount / 100.0) * 100.0
            ceiling = base + 100.0
            remanent = ceiling - amount

        result.append(
            Transaction(
                date=exp.date,
                amount=amount,
                ceiling=ceiling,
                remanent=remanent,
            )
        )
    return result


@router.post("/transactions:validator", response_model=ValidationResponse)
async def validate_transactions(request: ValidationRequest):
    seen_dates = set()
    valid = []
    invalid = []

    for t in request.transactions:
        is_valid = True
        fault_message = ""

        if t.amount < 0:
            is_valid, fault_message = False, "Negative amnt not allowed"
        elif t.amount >= 500000:
            is_valid, fault_message = False, "Exceeds max limit"
        elif t.date in seen_dates:
            is_valid, fault_message = False, "Duplicate date"

        if is_valid:
            valid.append(t)
            seen_dates.add(t.date)
        else:
            invalid.append(
                InvalidTransaction(
                    date=t.date,
                    amount=t.amount,
                    ceiling=t.ceiling,
                    remanent=t.remanent,
                    message=fault_message,
                )
            )

    return ValidationResponse(valid=valid, invalid=invalid)


@router.post("/transactions:filter", response_model=ValidationResponse)
async def filter_transactions(request: FilterRequest):
    valid = []
    invalid = []

    for t in request.transactions:
        updated_t, error_msg = apply_temporal_rules(t, request.q, request.p, request.k)

        if error_msg:
            invalid.append(
                InvalidTransaction(
                    date=t.date,
                    amount=t.amount,
                    ceiling=t.ceiling,
                    remanent=t.remanent,
                    message=error_msg,
                )
            )
        else:
            valid.append(updated_t)

    return ValidationResponse(valid=valid, invalid=invalid)
