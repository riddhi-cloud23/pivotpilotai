from fastapi import APIRouter, Depends

from backend.app.schemas import ChallengeBrief, ChallengeRequest, ChallengeResult, ChallengeSubmission
from backend.app.security import require_user
from backend.app.services.career import score_challenge
from backend.app.services.gemini import generate_structured

router = APIRouter(prefix="/api/v1/challenges", tags=["proof-of-skill"])


class _ChallengeEvaluation(ChallengeResult):
    pass


@router.post("/generate", response_model=ChallengeBrief)
async def generate_challenge(payload: ChallengeRequest, _user: str = Depends(require_user)) -> ChallengeBrief:
    prompt = (
        "Create an original practical skill challenge. It must assess submitted work rather than self-claims, "
        "fit the skill and level, and include observable evaluation criteria. "
        f"Request: {payload.model_dump_json()}"
    )
    generated = await generate_structured(prompt, ChallengeBrief)
    if generated:
        return generated
    return ChallengeBrief(
        challenge_id=f"demo-{payload.skill.lower().replace(' ', '-')}-{payload.difficulty}",
        title=f"{payload.difficulty.title()} {payload.skill} proof challenge",
        skill=payload.skill,
        difficulty=payload.difficulty,
        scenario=f"A team in a {payload.target_role} context needs evidence-based help with a realistic task involving {payload.skill}.",
        instructions=["State the problem and your assumptions.", "Show your proposed work or reasoning.", "Explain how you would validate the result and communicate limitations."],
        time_limit_minutes={"beginner": 30, "intermediate": 60, "advanced": 90}[payload.difficulty],
        evaluation_criteria=["Accuracy", "Reasoning", "Practicality", "Communication"],
    )


@router.post("/evaluate", response_model=ChallengeResult)
async def evaluate_challenge(payload: ChallengeSubmission, _user: str = Depends(require_user)) -> ChallengeResult:
    prompt = (
        "Assess the actual submitted work against the challenge and criteria. Never award credit for claims not evidenced "
        "in the submission. Return structured JSON including rubric scores, strengths, improvements, and next challenge. "
        f"Challenge: {payload.instructions}\nSubmission:\n{payload.submission}"
    )
    generated = await generate_structured(prompt, _ChallengeEvaluation)
    if generated:
        generated.ai_generated = True
        generated.record_id = generated.record_id or "assessment"
        return generated
    return score_challenge(payload)
