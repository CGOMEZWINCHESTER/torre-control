from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Contribution, Resident
from ..schemas import ResidentOut

MONTHLY_FEE = 850.0
AVATAR_COLORS = (
    "#b45309",
    "#2563eb",
    "#db2777",
    "#059669",
    "#7c3aed",
    "#dc2626",
    "#0891b2",
    "#ea580c",
    "#4f46e5",
    "#65a30d",
)


def avatar_for(name: str, dept_number: str) -> tuple[str, str]:
    initials = "".join(part[0] for part in name.split()[:2] if part).upper()[:2]
    index = ord(dept_number[0].upper()) - ord("A") if dept_number else 0
    return AVATAR_COLORS[index % len(AVATAR_COLORS)], initials or "🏠"


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
