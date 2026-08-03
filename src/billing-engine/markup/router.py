# Implements: WC027-01b — WC027-01ba
# constitutional_basis: C-059, C-082
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class MarkupRequest(BaseModel):
    """Request model for markup operations"""
    amount: float
    markup_percentage: float


class MarkupResponse(BaseModel):
    """Response model for markup operations"""
    original_amount: float
    markup_percentage: float
    markup_amount: float
    final_amount: float


@router.post("/calculate", response_model=MarkupResponse)
async def calculate_markup(request: MarkupRequest) -> MarkupResponse:
    """Calculate markup on an amount"""
    if request.amount < 0:
        raise HTTPException(status_code=400, detail="Amount cannot be negative")
    if request.markup_percentage < 0:
        raise HTTPException(status_code=400, detail="Markup percentage cannot be negative")
    
    markup_amount = request.amount * (request.markup_percentage / 100)
    final_amount = request.amount + markup_amount
    
    return MarkupResponse(
        original_amount=request.amount,
        markup_percentage=request.markup_percentage,
        markup_amount=markup_amount,
        final_amount=final_amount
    )


@router.get("/health")
async def markup_health() -> dict:
    """Health check for markup service"""
    return {"status": "healthy", "service": "markup"}