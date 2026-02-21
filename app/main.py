from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api import orchestrator, performance, returns, transactions

app = FastAPI(
    title="BlackRock Micro-Savings API",
    description="API for automated retirement savings through micro-investments",
    version="0.1.0",
)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# individual pipeline endpoints (as required by the PRD)
app.include_router(transactions.router, prefix="/blackrock/challenge/v1")
app.include_router(returns.router, prefix="/blackrock/challenge/v1")
app.include_router(performance.router, prefix="/blackrock/challenge/v1")

# orchestrator: runs the full pipeline in one call
app.include_router(orchestrator.router, prefix="/blackrock/challenge/v1")
