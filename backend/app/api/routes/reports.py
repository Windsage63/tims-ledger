from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.balances import ArAgingRead
from app.services.balances import ar_aging
from app.services.report_exports import ar_aging_csv, open_invoices_csv

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/ar-aging", response_model=ArAgingRead)
def get_ar_aging(
    session: Annotated[Session, Depends(get_session)],
    as_of_date: Annotated[date | None, Query()] = None,
) -> dict:
    return ar_aging(session, as_of_date or date.today())


@router.get("/ar-aging.csv", response_class=Response)
def download_ar_aging_csv(
    session: Annotated[Session, Depends(get_session)],
    as_of_date: Annotated[date | None, Query()] = None,
) -> Response:
    csv_text = ar_aging_csv(session, as_of_date or date.today())
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ar-aging.csv"},
    )


@router.get("/open-invoices.csv", response_class=Response)
def download_open_invoices_csv(
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    return Response(
        content=open_invoices_csv(session),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=open-invoices.csv"},
    )
