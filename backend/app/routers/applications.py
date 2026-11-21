from fastapi import APIRouter, Depends

from backend.app.schemas import ApplicationAnalysis, ApplicationRecord
from backend.app.security import require_user
from backend.app.services.career import application_insights

router = APIRouter(prefix="/api/v1/applications", tags=["applications"])


@router.post("/analyze", response_model=ApplicationAnalysis)
def analyze_applications(records: list[ApplicationRecord], _user: str = Depends(require_user)) -> ApplicationAnalysis:
    return application_insights(records)
