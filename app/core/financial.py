import math

from app.core.temporal import is_in_k_period, parse_date
from app.models.schemas import KPeriod, SavingsByDate, Transaction

NPS_RATE = 0.0711
INDEX_RATE = 0.1449


def calculate_time(age: int) -> int:
    return 60 - age if age < 60 else 5


def calculate_compound_interest(principal: float, rate: float, t: int) -> float:
    # A = P(1+r)^t
    return principal * math.pow(1 + rate, t)


def calculate_inflation_adjustment(amount: float, inflation: float, t: int) -> float:
    # Areal = A / (1+inflation)^t
    return amount / math.pow(1 + inflation, t)


def calculate_tax(income: float) -> float:
    """Calculates tax based on the simplified slabs."""
    tax = 0.0

    if income > 1500000:
        tax += (income - 1500000) * 0.30
        income = 1500000
    if income > 1200000:
        tax += (income - 1200000) * 0.20
        income = 1200000
    if income > 1000000:
        tax += (income - 1000000) * 0.15
        income = 1000000
    if income > 700000:
        tax += (income - 700000) * 0.10
        income = 700000

    return tax


def calculate_tax_benefit(amount_invested: float, annual_wage: float) -> float:
    """Calculates tax benefit for NPS."""
    nps_deduction = min(amount_invested, annual_wage * 0.10, 200000.0)
    tax_no_deduction = calculate_tax(annual_wage)
    tax_with_deduction = calculate_tax(max(0.0, annual_wage - nps_deduction))
    return tax_no_deduction - tax_with_deduction


def group_savings_by_k(
    transactions: list[Transaction], k_periods: list[KPeriod]
) -> list[SavingsByDate]:
    """Groups transaction remanents by K periods."""
    savings = []

    for k in k_periods:
        total = 0.0
        for t in transactions:
            t_date = parse_date(t.date)
            if t_date and is_in_k_period(t_date, k):
                total += t.remanent

        savings.append(
            SavingsByDate(
                start=k.start,
                end=k.end,
                amount=total,
                profits=0.0,  # Will be set by specific return handlers
                tax_benefit=0.0,
            )
        )

    return savings
