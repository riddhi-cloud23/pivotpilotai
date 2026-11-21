from fastapi import APIRouter, Depends

from backend.app.schemas import MarketValue, MarketValueRequest
from backend.app.security import require_user
from backend.app.services.career import estimate_market_value

router = APIRouter(prefix="/api/v1/market", tags=["market-value"])


@router.post("/estimate", response_model=MarketValue)
def market_estimate(payload: MarketValueRequest, _user: str = Depends(require_user)) -> MarketValue:
    return estimate_market_value(payload.target_role, payload.location, payload.verified_skills, payload.completed_projects, payload.interview_score)
