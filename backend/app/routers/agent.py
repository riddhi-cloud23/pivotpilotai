from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from backend.app.schemas import AgentReport, ApplicationRecord, OpportunityPreferences
from backend.app.security import require_user
from backend.app.services.career import build_agent_report
from backend.app.services.gemini import generate_structured

router = APIRouter(prefix="/api/v1/agent", tags=["career-agent"])


@router.post("/weekly-report", response_model=AgentReport)
async def weekly_report(
    preferences: OpportunityPreferences,
    completed_tasks: int = 0,
    missing_skills: list[str] | None = None,
    upcoming_deadlines: list[str] | None = None,
    _user: str = Depends(require_user),
) -> AgentReport:
    missing_skills = missing_skills or []
    upcoming_deadlines = upcoming_deadlines or []
    report = build_agent_report(
        preferences.target_role,
        preferences.location,
        max(0, completed_tasks),
        upcoming_deadlines,
        missing_skills,
    )
    prompt = (
        "Write a concise personalized weekly career report from the supplied data. Explain match reasons, missing skills, "
        "progress, deadlines, and portfolio improvements. Do not invent live job openings or claim to monitor in the background. "
        "Never submit applications, send messages, or perform external actions. Keep pending_approvals empty unless an action "
        "was explicitly requested. Return the required schema.\n"
        f"Data: {report.model_dump_json()}"
    )
    generated = await generate_structured(prompt, AgentReport)
    if generated:
        generated.generated_at = datetime.now(timezone.utc)
        generated.ai_generated = True
        generated.pending_approvals = []
        return generated
    return report


@router.post("/opportunities/match")
def match_opportunities(
    preferences: OpportunityPreferences,
    records: list[ApplicationRecord] | None = None,
    _user: str = Depends(require_user),
) -> dict[str, object]:
    del records
    return {
        "opportunities": [
            {
                "title": f"Entry-level {preferences.target_role}",
                "location": preferences.location,
                "match": 58,
                "source": "Demo recommendation — configure a verified job-search provider for live vacancies.",
                "missing_qualifications": ["No live job description has been evaluated yet."],
                "requires_approval": False,
            }
        ],
        "monitoring": "On-demand demo only. Scheduled monitoring and notifications require a deployed worker and configured job source.",
        "external_actions_performed": [],
    }
