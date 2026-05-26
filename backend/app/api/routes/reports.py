from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.balances import ArAgingRead
from app.services.balances import ar_aging

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/ar-aging", response_model=ArAgingRead)
def get_ar_aging(
    session: Annotated[Session, Depends(get_session)],
    as_of_date: Annotated[date | None, Query()] = None,
) -> dict:
    return ar_aging(session, as_of_date or date.today())
