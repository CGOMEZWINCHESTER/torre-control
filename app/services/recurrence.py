from calendar import monthrange
from datetime import date, timedelta

from ..schemas import Frequency


def next_due_date(current: date | None, frequency: Frequency) -> date | None:
    base = current or date.today()

    if frequency == "Semanal":
        return base + timedelta(days=7)

    if frequency == "Mensual":
        year = base.year + base.month // 12
        month = base.month % 12 + 1
        day = min(base.day, monthrange(year, month)[1])
        return date(year, month, day)

    return base
