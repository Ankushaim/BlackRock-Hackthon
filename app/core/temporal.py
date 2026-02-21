from datetime import datetime

from app.models.schemas import KPeriod, PPeriod, QPeriod, Transaction

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def parse_date(date_str: str) -> datetime | None:
    try:
        return datetime.strptime(date_str, DATE_FORMAT)
    except ValueError:
        return None


def apply_temporal_rules(
    transaction: Transaction,
    q_periods: list[QPeriod],
    p_periods: list[PPeriod],
    k_periods: list[KPeriod],
) -> tuple[Transaction | None, str | None]:
    """
    Applies q and p temporal rules on a transaction.
    Returns (Transaction, error_message).
    If error_message is not None, the transaction is functionally invalid.
    """
    t_date = parse_date(transaction.date)
    if not t_date:
        return None, "Invalid date format"

    # Deep copy the transaction
    updated_transaction = transaction.model_copy()

    # Process Q periods
    matching_q = []
    for i, q in enumerate(q_periods):
        q_start = parse_date(q.start)
        q_end = parse_date(q.end)
        if q_start and q_end and q_start <= t_date <= q_end:
            matching_q.append((q, i, q_start))

    if matching_q:
        # Sort by: latest start date (descending), then original index (ascending)
        matching_q.sort(key=lambda x: (x[2], -x[1]), reverse=True)
        chosen_q = matching_q[0][0]
        updated_transaction.remanent = chosen_q.fixed

    # Process P periods
    matching_p_extra = 0.0
    for p in p_periods:
        p_start = parse_date(p.start)
        p_end = parse_date(p.end)
        if p_start and p_end and p_start <= t_date <= p_end:
            matching_p_extra += p.extra

    updated_transaction.remanent += matching_p_extra
    return updated_transaction, None


def is_in_k_period(t_date: datetime, k: KPeriod) -> bool:
    k_start = parse_date(k.start)
    k_end = parse_date(k.end)
    if k_start and k_end:
        return k_start <= t_date <= k_end
    return False
