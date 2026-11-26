from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import admin_only, get_current_user
from ..models import Contribution, Expense, Resident
from ..schemas import (
    ContributionCreate,
    ContributionOut,
    ContributionReview,
    ExpenseCreate,
    ExpenseOut,
    ExpenseUpdate,
    FinanceSummaryOut,
    MessageOut,
    ResidentOut,
)
from ..services.images import validate_image_data_url
from ..services.residents import current_period, resident_out_map

router = APIRouter(prefix="/api", tags=["finance"])

OPENING_BALANCE = 0


def _load_expense(expense_id: int, db: Session) -> Expense | None:
    return db.scalar(
        select(Expense)
        .options(joinedload(Expense.creator))
        .execution_options(populate_existing=True)
        .where(Expense.id == expense_id)
    )


def _require_expense(expense_id: int, db: Session) -> Expense:
    expense = _load_expense(expense_id, db)
    if expense is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Egreso no encontrado",
        )
    return expense


def _expense_out(expense: Expense, residents: dict[int, ResidentOut]) -> ExpenseOut:
    return ExpenseOut.model_validate(expense).model_copy(
        update={"creator": residents[expense.created_by]}
    )


def _load_contribution(contribution_id: int, db: Session) -> Contribution | None:
    return db.scalar(
        select(Contribution)
        .options(joinedload(Contribution.resident), joinedload(Contribution.approver))
        .execution_options(populate_existing=True)
        .where(Contribution.id == contribution_id)
    )


def _require_contribution(contribution_id: int, db: Session) -> Contribution:
    contribution = _load_contribution(contribution_id, db)
    if contribution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aportación no encontrada",
        )
    return contribution


def _contribution_out(
    contribution: Contribution,
    residents: dict[int, ResidentOut],
) -> ContributionOut:
    return ContributionOut.model_validate(contribution).model_copy(
        update={
            "resident": residents[contribution.resident_id],
            "approver": residents.get(contribution.approved_by),
        }
    )


@router.get("/expenses", response_model=list[ExpenseOut])
def list_expenses(
    db: Session = Depends(get_db),
    current_user: Resident = Depends(get_current_user),
):
    expenses = db.scalars(
        select(Expense).order_by(Expense.spent_on.desc(), Expense.id.desc())
    ).all()
    residents = resident_out_map(db)
    return [_expense_out(expense, residents) for expense in expenses]


@router.post("/expenses", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(admin_only),
):
    values = payload.model_dump()
    values["receipt_url"] = validate_image_data_url(values["receipt_url"])
    expense = Expense(**values, created_by=current_user.id)
    db.add(expense)
    db.commit()
    return _expense_out(_require_expense(expense.id, db), resident_out_map(db))


@router.patch("/expenses/{expense_id}", response_model=ExpenseOut)
def update_expense(
    expense_id: int,
    payload: ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(admin_only),
):
    expense = _require_expense(expense_id, db)
    values = payload.model_dump(exclude_unset=True)
    if "receipt_url" in values:
        values["receipt_url"] = validate_image_data_url(values["receipt_url"])
    for field, value in values.items():
        setattr(expense, field, value)
    db.commit()
    return _expense_out(_require_expense(expense_id, db), resident_out_map(db))


@router.delete("/expenses/{expense_id}", response_model=MessageOut)
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(admin_only),
):
    expense = _require_expense(expense_id, db)
    db.delete(expense)
    db.commit()
    return MessageOut(message="Egreso eliminado")


@router.get("/contributions", response_model=list[ContributionOut])
def list_contributions(
    db: Session = Depends(get_db),
    current_user: Resident = Depends(get_current_user),
):
    contributions = db.scalars(
        select(Contribution).order_by(Contribution.created_at.desc(), Contribution.id.desc())
    ).all()
    residents = resident_out_map(db)
    return [_contribution_out(contribution, residents) for contribution in contributions]


@router.post("/contributions", response_model=ContributionOut, status_code=status.HTTP_201_CREATED)
def create_contribution(
    payload: ContributionCreate,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(get_current_user),
):
    values = payload.model_dump()
    values["proof_url"] = validate_image_data_url(values["proof_url"])
    resident_id = values.pop("resident_id") or current_user.id
    if db.get(Resident, resident_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Residente no encontrado",
        )

    contribution = Contribution(
        resident_id=resident_id,
        kind=values["kind"],
        period=values["period"],
        amount=values["amount"],
        proof_url=values["proof_url"],
        status="Pendiente",
    )
    db.add(contribution)
    db.commit()
    return _contribution_out(_require_contribution(contribution.id, db), resident_out_map(db))


@router.post("/contributions/{contribution_id}/review", response_model=ContributionOut)
def review_contribution(
    contribution_id: int,
    payload: ContributionReview,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(admin_only),
):
    contribution = _require_contribution(contribution_id, db)
    if payload.action == "approve":
        contribution.status = "Aprobada"
        contribution.approved_at = datetime.now(timezone.utc)
        contribution.approved_by = current_user.id
    else:
        contribution.status = "Rechazada"
        contribution.approved_at = None
        contribution.approved_by = None
    db.commit()
    return _contribution_out(_require_contribution(contribution_id, db), resident_out_map(db))


@router.get("/finance/summary", response_model=FinanceSummaryOut)
def finance_summary(
    db: Session = Depends(get_db),
    current_user: Resident = Depends(get_current_user),
):
    period = current_period()
    year, month = (int(part) for part in period.split("-"))
    month_start = date(year, month, 1)
    next_month = date(year + month // 12, month % 12 + 1, 1)

    approved_total = db.scalar(
        select(func.coalesce(func.sum(Contribution.amount), 0.0)).where(
            Contribution.status == "Aprobada"
        )
    )
    collected = db.scalar(
        select(func.coalesce(func.sum(Contribution.amount), 0.0)).where(
            Contribution.status == "Aprobada",
            Contribution.period == period,
        )
    )
    spent = db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0.0)).where(
            Expense.spent_on >= month_start,
            Expense.spent_on < next_month,
        )
    )
    pending = db.scalar(
        select(func.count()).select_from(Contribution).where(
            Contribution.status == "Pendiente"
        )
    )

    return FinanceSummaryOut(
        opening_balance=OPENING_BALANCE,
        cash_balance=OPENING_BALANCE + float(approved_total or 0.0) - float(spent or 0.0),
        collected_this_month=float(collected or 0.0),
        spent_this_month=float(spent or 0.0),
        pending_reviews=int(pending or 0),
    )
