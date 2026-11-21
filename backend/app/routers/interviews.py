from fastapi import APIRouter, Depends

from backend.app.schemas import InterviewQuestionResponse, InterviewRequest, InterviewScore
from backend.app.security import require_user
from backend.app.services.career import score_text_answer
from backend.app.services.gemini import generate_structured

router = APIRouter(prefix="/api/v1/interviews", tags=["mock-interviews"])


@router.post("/question", response_model=InterviewQuestionResponse)
async def next_question(payload: InterviewRequest, _user: str = Depends(require_user)) -> InterviewQuestionResponse:
    prompt = (
        "Create one original, role-relevant mock interview question. Do not claim it is a verbatim real interview question. "
        f"Target role: {payload.target_role}. Focus on: {', '.join(payload.weak_skills) or 'role fundamentals'}."
    )
    generated = await generate_structured(prompt, InterviewQuestionResponse)
    if generated and generated.question:
        generated.source_note = "Original practice prompt generated for this session."
        return generated
    topic = payload.weak_skills[0] if payload.weak_skills else "your approach"
    return InterviewQuestionResponse(
        question=f"For a {payload.target_role} role, describe how you would use {topic} to solve a realistic problem. What would you measure, and what trade-off would you explain?",
        source_note="Original demo practice prompt; not represented as a verbatim interview question.",
    )


@router.post("/score", response_model=InterviewScore)
async def score_answer(payload: InterviewRequest, _user: str = Depends(require_user)) -> InterviewScore:
    if not payload.answer:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="Provide an interview answer to score.")
    prompt = (
        "Evaluate only the submitted answer. Score technical_accuracy, depth, structure, and clarity 0-25 each. "
        "Offer a concise constructive correction and a follow-up. Do not claim a definitive hiring outcome. "
        f"Return the required schema.\nRole: {payload.target_role}\nQuestion: {payload.question}\n"
        f"Weak topics: {payload.weak_skills}\nAnswer: {payload.answer}"
    )
    generated = await generate_structured(prompt, InterviewScore)
    if generated:
        generated.ai_generated = True
        generated.total = generated.technical_accuracy + generated.depth + generated.structure + generated.clarity
        return generated
    return score_text_answer(payload.answer, payload.target_role, payload.question, payload.weak_skills)
