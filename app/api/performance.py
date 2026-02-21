import threading
import time

import psutil
from fastapi import APIRouter

from app.models.schemas import PerformanceResponse

router = APIRouter()

start_time = time.time()


def get_uptime() -> str:
    uptime_seconds = int(time.time() - start_time)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.000"


@router.get("/performance", response_model=PerformanceResponse)
async def get_performance():
    process = psutil.Process()
    memory_info = process.memory_info()
    memory_mb = memory_info.rss / (1024 * 1024)

    return PerformanceResponse(
        time=get_uptime(),
        memory=f"{memory_mb:.2f} MB",
        threads=threading.active_count(),
    )
