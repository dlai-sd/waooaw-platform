# Implements: WC027-01b — WC027-01ba
# constitutional_basis: C-059, C-082
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class MarkupRequest(BaseModel):
    base_amount: float
    markup_percentage: float


class MarkupResponse(BaseModel):
    base_amount: float
    markup_percentage: float
    markup_amount: float
    total_amount: float


@router.post("/calculate", response_model=MarkupResponse)
async def calculate_markup(request: MarkupRequest) -> MarkupResponse:
    """Calculate markup on a base amount"""
    if request.base_amount < 0:
        raise HTTPException(status_code=400, detail="Base amount cannot be negative")
    if request.markup_percentage < 0:
        raise HTTPException(status_code=400, detail="Markup percentage cannot be negative")
    
    markup_amount = request.base_amount * (request.markup_percentage / 100)
    total_amount = request.base_amount + markup_amount
    
    return MarkupResponse(
        base_amount=request.base_amount,
        markup_percentage=request.markup_percentage,
        markup_amount=markup_amount,
        total_amount=total_amount
    )

# src/billing-engine/main.py
# Implements: WC027-01b — WC027-01ba
# constitutional_basis: C-059, C-082
app = FastAPI()
app.include_router(router, prefix="/markup", tags=["markup"])
