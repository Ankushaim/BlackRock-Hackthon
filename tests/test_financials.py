from fastapi.testclient import TestClient

from app.core.financial import (
    calculate_compound_interest,
    calculate_inflation_adjustment,
    calculate_tax,
    calculate_tax_benefit,
)
from app.main import app

"""
1. Test type: Unit and Integration Test
2. Validation to be executed: Verifies core financial formulas (compound interest, tax slabs, inflation logic) and endpoints health check.
3. Command with the necessary arguments for execution: `uv run pytest test/`
"""

client = TestClient(app)


def test_health_check():
    """Integration: Test API is healthy"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_compound_interest():
    """Unit: Compounding at 10% for 2 years on 1000"""
    result = calculate_compound_interest(1000.0, 0.10, 2)
    # 1000 * (1.1)^2 = 1210
    assert round(result, 2) == 1210.0


def test_inflation_adjustment():
    """Unit: Adjusting for 5% inflation over 2 years on 1210"""
    result = calculate_inflation_adjustment(1210.0, 0.05, 2)
    # 1210 / (1.05)^2 = 1097.505...
    assert round(result, 2) == 1097.51


def test_tax_no_income():
    """Unit: Tax on exactly 700k (0%)"""
    tax = calculate_tax(700000)
    assert tax == 0.0


def test_tax_high_income():
    """Unit: Tax on 1600k (spanning tiers up to 30%)"""
    tax = calculate_tax(1600000)
    # Tiers:
    # > 1.5M: 100k @ 30% = 30k
    # > 1.2M: 300k @ 20% = 60k
    # > 1.0M: 200k @ 15% = 30k
    # > 0.7M: 300k @ 10% = 30k
    # Total = 150k
    assert tax == 150000.0


def test_tax_benefit():
    """Unit: Calculate net tax benefit from NPS investment"""
    # Wage 1500000
    # Tax without deduction:
    # 300k * 20% = 60k
    # 200k * 15% = 30k
    # 300k * 10% = 30k
    # Total = 120k

    # 10% of wage = 150k
    # If we invest 100k, we can deduct up to 100k.
    # Tax with deduction (income = 1400000):
    # 200k * 20% = 40k
    # 200k * 15% = 30k
    # 300k * 10% = 30k
    # Total = 100k

    # Benefit = 120k - 100k = 20k
    benefit = calculate_tax_benefit(100000.0, 1500000.0)
    assert benefit == 20000.0
