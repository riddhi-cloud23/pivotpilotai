from datetime import datetime, timezone
import re

from fastapi import APIRouter, Depends

from backend.app.schemas import (
    BulletRequest,
    BulletResponse,
    MilestoneVerification,
    MilestoneVerifyRequest,
    ProjectRequest,
    ProjectResponse,
)
from backend.app.security import require_user
from backend.app.services.career import recommend_projects
from backend.app.services.gemini import generate_structured

router = APIRouter(prefix="/api/v1/portfolio", tags=["portfolio-and-resume"])


class _BulletSchema(BulletResponse):
    pass


@router.post("/projects", response_model=ProjectResponse)
async def projects(payload: ProjectRequest, _user: str = Depends(require_user)) -> ProjectResponse:
    prompt = (
        "Create two realistic portfolio project briefs that bridge prior experience to target role skill gaps. "
        "Keep scope feasible for an individual. Provide measurable deliverables but invent no user outcomes. "
        f"Return the required JSON schema. Request: {payload.model_dump_json()}"
    )
    result = await generate_structured(prompt, ProjectResponse)
    if result:
        result.ai_generated = True
        return result
    return recommend_projects(payload)


@router.post("/verify", response_model=MilestoneVerification)
def verify_milestone(payload: MilestoneVerifyRequest, _user: str = Depends(require_user)) -> MilestoneVerification:
    specificity = [bool(re.search(r"\b(why|because|trade.?off|test|result|metric|example|method|decision)\b", answer, re.I)) for answer in payload.answers]
    nonempty = [bool(answer.strip()) for answer in payload.answers]
    score = round((sum(specificity) / 3 * 60) + (sum(nonempty) / 3 * 40))
    return MilestoneVerification(
        passed=score >= 65,
        score=score,
        feedback=[
            "The check evaluates explanation and evidence, not just a completion checkbox.",
            *(["Add a concrete example to make the skill easier to verify."] if score < 65 else ["The answers show enough evidence to propose a resume bullet for your review."]),
        ],
    )


@router.post("/resume/bullets", response_model=BulletResponse)
async def resume_bullets(payload: BulletRequest, _user: str = Depends(require_user)) -> BulletResponse:
    prompt = (
        "Draft up to three ATS-friendly resume bullets from only this evidence. "
        "Do not invent metrics, employers, tools, or outcomes. Use placeholders in brackets where evidence is missing. "
        f"Return the required JSON schema. Target role: {payload.target_role}. Milestone: {payload.milestone_title}. Evidence: {payload.evidence}"
    )
    result = await generate_structured(prompt, BulletResponse)
    if result:
        result.ai_generated = True
        return result
    text = payload.evidence.strip().rstrip(".")
    return BulletResponse(bullets=[f"Completed {payload.milestone_title} for {payload.target_role}, demonstrating {text[:220] or '[describe verified work and outcome]'}." ])


@router.get("/roles")
def unlocked_roles(target_role: str, verified_skills: str = "", _user: str = Depends(require_user)) -> dict[str, object]:
    skills = {skill.strip().lower() for skill in verified_skills.split(",") if skill.strip()}
    match = min(95, 40 + len(skills) * 7)
    return {"roles": [{"title": target_role, "match": match, "evidence": "Directional demo match based on supplied verified skills.", "requirements_to_check": ["Compare against each employer's full job description."]}]}
