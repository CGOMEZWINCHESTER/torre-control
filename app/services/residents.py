from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Contribution, Resident
from ..schemas import ResidentOut

MONTHLY_FEE = 850.0


def current_period() -> str:
    return date.today().strftime("%Y-%m")


def paid_by_resident(db: Session, period: str | None = None) -> dict[int, float]:
    period = period or current_period()
    rows = db.execute(
        select(Contribution.resident_id, func.coalesce(func.sum(Contribution.amount), 0.0))
        .where(
            Contribution.status == "Aprobada",
            Contribution.period == period,
        )
        .group_by(Contribution.resident_id)
    ).all()
    return {resident_id: float(total or 0.0) for resident_id, total in rows}


def resident_out(resident: Resident, amount_paid: float = 0.0) -> ResidentOut:
    amount = float(amount_paid)
    return ResidentOut.model_validate(resident).model_copy(
        update={
            "amount_paid": amount,
            "account_status": "Al corriente" if amount >= MONTHLY_FEE else "Con adeudo",
        }
    )


def resident_out_map(
    db: Session,
    residents: list[Resident] | None = None,
) -> dict[int, ResidentOut]:
    paid = paid_by_resident(db)
    if residents is None:
        residents = db.scalars(select(Resident).order_by(Resident.id.asc())).all()
    return {resident.id: resident_out(resident, paid.get(resident.id, 0.0)) for resident in residents}
