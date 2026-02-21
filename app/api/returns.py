import uuid
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException

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
    JobResponse,
    JobStatusResponse,
    ReturnsRequest,
    ReturnsResponse,
)

router = APIRouter()

# In-memory store for async jobs
JOBS: Dict[str, Dict[str, Any]] = {}


def process_returns(request: ReturnsRequest, is_nps: bool) -> ReturnsResponse:
    filtered_transactions = []
    total_amount = 0.0
    total_ceiling = 0.0

    for t in request.transactions:
        updated_t, error = apply_temporal_rules(t, request.q, request.p, request.k)
        if not error and updated_t:
            filtered_transactions.append(updated_t)
            total_amount += updated_t.amount
            total_ceiling += updated_t.ceiling

    savings_by_dates = group_savings_by_k(filtered_transactions, request.k)
    t_years = calculate_time(request.age)
    annual_wage = request.wage * 12  # wage input is monthly based on PRD

    for s in savings_by_dates:
        if s.amount > 0:
            rate = NPS_RATE if is_nps else INDEX_RATE
            future_value = calculate_compound_interest(s.amount, rate, t_years)
            real_fv = calculate_inflation_adjustment(
                future_value, request.inflation, t_years
            )
            s.profits = round(real_fv - s.amount, 2)

            if is_nps:
                s.tax_benefit = round(calculate_tax_benefit(s.amount, annual_wage), 2)

    return ReturnsResponse(
        transactions_total_amount=round(total_amount, 2),
        transactions_total_ceiling=round(total_ceiling, 2),
        savings_by_dates=savings_by_dates,
    )


def background_process_returns(job_id: str, request: ReturnsRequest, is_nps: bool):
    """Background task to process returns to prevent blocking or timeouts."""
    try:
        result = process_returns(request, is_nps)
        JOBS[job_id] = {"status": "completed", "result": result, "error": None}
    except Exception as e:
        JOBS[job_id] = {"status": "failed", "result": None, "error": str(e)}


@router.post("/returns:nps", response_model=ReturnsResponse)
async def calculate_nps(request: ReturnsRequest):
    return process_returns(request, is_nps=True)


@router.post("/returns:index", response_model=ReturnsResponse)
async def calculate_index(request: ReturnsRequest):
    return process_returns(request, is_nps=False)


@router.post("/returns:nps:async", response_model=JobResponse)
async def calculate_nps_async(
    request: ReturnsRequest, background_tasks: BackgroundTasks
):
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "processing", "result": None, "error": None}
    background_tasks.add_task(background_process_returns, job_id, request, is_nps=True)
    return JobResponse(job_id=job_id, status="processing")


@router.post("/returns:index:async", response_model=JobResponse)
async def calculate_index_async(
    request: ReturnsRequest, background_tasks: BackgroundTasks
):
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "processing", "result": None, "error": None}
    background_tasks.add_task(background_process_returns, job_id, request, is_nps=False)
    return JobResponse(job_id=job_id, status="processing")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")

    job = JOBS[job_id]
    return JobStatusResponse(
        job_id=job_id, status=job["status"], result=job["result"], error=job["error"]
    )
