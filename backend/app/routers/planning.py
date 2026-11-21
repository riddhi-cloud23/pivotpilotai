from fastapi import APIRouter, Depends

from backend.app.schemas import PlanRequest, PlanResponse
from backend.app.security import require_user
from backend.app.services.career import build_learning_plan

router = APIRouter(prefix="/api/v1/planner", tags=["planner"])


@router.post("/generate", response_model=PlanResponse)
def generate_plan(payload: PlanRequest, _user: str = Depends(require_user)) -> PlanResponse:
    return build_learning_plan(payload)


@router.post("/reschedule", response_model=PlanResponse)
def reschedule_plan(payload: PlanRequest, _user: str = Depends(require_user)) -> PlanResponse:
    return build_learning_plan(payload)
