from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Expense(CamelModel):
    date: str = Field(..., description="Date-time in format YYYY-MM-DD HH:mm:ss")
    amount: float


class Transaction(Expense):
    ceiling: float
    remanent: float


class InvalidTransaction(Transaction):
    message: str


class ValidationRequest(CamelModel):
    wage: float
    transactions: list[Transaction]


class ValidationResponse(CamelModel):
    valid: list[Transaction]
    invalid: list[InvalidTransaction]


class QPeriod(CamelModel):
    fixed: float
    start: str
    end: str


class PPeriod(CamelModel):
    extra: float
    start: str
    end: str


class KPeriod(CamelModel):
    start: str
    end: str


class FilterRequest(CamelModel):
    q: list[QPeriod] = []
    p: list[PPeriod] = []
    k: list[KPeriod] = []
    transactions: list[Transaction]


class ReturnsRequest(CamelModel):
    age: int
    wage: float
    inflation: float
    q: list[QPeriod] = []
    p: list[PPeriod] = []
    k: list[KPeriod] = []
    transactions: list[Transaction]


class SavingsByDate(CamelModel):
    start: str
    end: str
    amount: float
    profits: float
    tax_benefit: float = 0.0


class ReturnsResponse(CamelModel):
    transactions_total_amount: float
    transactions_total_ceiling: float
    savings_by_dates: list[SavingsByDate]


class PerformanceResponse(CamelModel):
    time: str
    memory: str
    threads: int


class JobResponse(CamelModel):
    job_id: str
    status: str


class JobStatusResponse(CamelModel):
    job_id: str
    status: str
    result: ReturnsResponse | None = None
    error: str | None = None
