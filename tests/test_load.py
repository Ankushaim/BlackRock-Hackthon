"""
1. Test type: Load / Performance Test
2. Validation to be executed:
   - Tests all core endpoints at increasing scales: 1_000 → 10_000 → 100_000 transactions
   - Measures wall-clock response time per scale tier
   - Checks /performance endpoint for system-level memory and thread metrics
   - Verifies that the API completes successfully (status 200) at all scales
3. Command with the necessary arguments for execution:
   PYTHONPATH=. uv run pytest tests/test_load.py -v -s
"""

import random
import time
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

BASE_DATE = datetime(2023, 1, 1)


def make_expenses(n: int) -> list[dict]:
    """Generate n unique expenses across year 2023."""
    step = timedelta(seconds=365 * 24 * 3600 // (n + 1))
    return [
        {
            "date": (BASE_DATE + step * i).strftime("%Y-%m-%d %H:%M:%S"),
            "amount": round(random.uniform(10, 499999), 2),
        }
        for i in range(n)
    ]


def make_periods(n: int, field: str, value: float) -> list[dict]:
    """Spread n short non-overlapping periods across 2023."""
    step = timedelta(days=365 // max(n, 1))
    periods = []
    for i in range(min(n, 365)):  # cap at 365 so they stay in year
        start = BASE_DATE + step * i
        end = start + timedelta(hours=12)
        p = {
            "start": start.strftime("%Y-%m-%d %H:%M:%S"),
            "end": end.strftime("%Y-%m-%d %H:%M:%S"),
        }
        p[field] = value
        periods.append(p)
    return periods


SCALES = [1_000, 10_000, 100_000]


@pytest.mark.parametrize("n", SCALES)
def test_parse_at_scale(n: int):
    """
    Hits /transactions:parse with n expenses.
    Verifies status 200 and logs elapsed time.
    """
    expenses = make_expenses(n)
    t0 = time.perf_counter()
    resp = client.post("/blackrock/challenge/v1/transactions:parse", json=expenses)
    elapsed = time.perf_counter() - t0

    assert resp.status_code == 200
    result = resp.json()
    assert len(result) == n
    print(
        f"\n  [parse] n={n:>7,} | time={elapsed:.3f}s | first_remanent={result[0]['remanent']}"
    )


@pytest.mark.parametrize("n", SCALES)
def test_validator_at_scale(n: int):
    """
    Hits /transactions:validator with n transactions.
    5% of transactions have negative amounts to trigger invalid path.
    """
    expenses = make_expenses(n)
    # parse first to get proper ceiling/remanent
    parsed = client.post(
        "/blackrock/challenge/v1/transactions:parse", json=expenses
    ).json()
    # intentionally poison ~5%
    for i in range(0, n, 20):
        parsed[i]["amount"] = -1.0

    payload = {"wage": 80000, "transactions": parsed}
    t0 = time.perf_counter()
    resp = client.post("/blackrock/challenge/v1/transactions:validator", json=payload)
    elapsed = time.perf_counter() - t0

    assert resp.status_code == 200
    body = resp.json()
    print(
        f"\n  [validator] n={n:>7,} | time={elapsed:.3f}s "
        f"| valid={len(body['valid'])} | invalid={len(body['invalid'])}"
    )


@pytest.mark.parametrize("n", SCALES)
def test_filter_at_scale(n: int):
    """
    Hits /transactions:filter with n transactions and q+p+k periods.
    Uses a smaller number of periods to keep payload sane while still testing logic.
    """
    expenses = make_expenses(n)
    parsed = client.post(
        "/blackrock/challenge/v1/transactions:parse", json=expenses
    ).json()

    payload = {
        "q": make_periods(10, "fixed", 50.0),
        "p": make_periods(10, "extra", 25.0),
        "k": [
            {"start": "2023-01-01 00:00:00", "end": "2023-06-30 23:59:59"},
            {"start": "2023-07-01 00:00:00", "end": "2023-12-31 23:59:59"},
        ],
        "transactions": parsed,
    }

    t0 = time.perf_counter()
    resp = client.post("/blackrock/challenge/v1/transactions:filter", json=payload)
    elapsed = time.perf_counter() - t0

    assert resp.status_code == 200
    body = resp.json()
    print(f"\n  [filter] n={n:>7,} | time={elapsed:.3f}s | valid={len(body['valid'])}")


@pytest.mark.parametrize("n", SCALES)
def test_calculate_orchestrator_at_scale(n: int):
    """
    Hits the /calculate orchestrator with n raw expenses.
    This is the most expensive test — it runs the full pipeline.
    """
    expenses = make_expenses(n)

    payload = {
        "age": 30,
        "wage": 80000,
        "inflation": 0.055,
        "q": make_periods(5, "fixed", 0.0),
        "p": make_periods(5, "extra", 10.0),
        "k": [
            {"start": "2023-01-01 00:00:00", "end": "2023-06-30 23:59:59"},
            {"start": "2023-07-01 00:00:00", "end": "2023-12-31 23:59:59"},
        ],
        "expenses": expenses,
    }

    t0 = time.perf_counter()
    resp = client.post("/blackrock/challenge/v1/calculate", json=payload)
    elapsed = time.perf_counter() - t0

    assert resp.status_code == 200
    body = resp.json()
    print(
        f"\n  [calculate] n={n:>7,} | time={elapsed:.3f}s "
        f"| parsed={body['summary']['parsed']} "
        f"| rejected={body['summary']['rejected']}"
    )


def test_performance_endpoint():
    """
    Verifies the /performance endpoint returns valid metrics after load.
    """
    resp = client.get("/blackrock/challenge/v1/performance")
    assert resp.status_code == 200
    body = resp.json()

    assert "time" in body
    assert "MB" in body["memory"]
    assert body["threads"] >= 1
    print(f"\n  [performance] {body}")
