from fastapi import APIRouter, Depends, HTTPException

from backend.app.schemas import DiagnosticQuestion, DiagnosticAnswerRequest, DiagnosticResult
from backend.app.security import require_user
from backend.app.services.career import QUIZ_BANK, grade_diagnostic, next_diagnostic_question

router = APIRouter(prefix="/api/v1/diagnostic", tags=["diagnostic"])


@router.post("/question", response_model=DiagnosticQuestion)
def get_question(target_role: str, history: list[dict[str, object]] | None = None, _user: str = Depends(require_user)) -> DiagnosticQuestion:
    history = history or []
    if len(history) >= 12:
        raise HTTPException(status_code=409, detail="The 12-question diagnostic is complete.")
    return next_diagnostic_question(target_role, history, len(history))


@router.post("/answer", response_model=DiagnosticResult)
def answer(payload: DiagnosticAnswerRequest, _user: str = Depends(require_user)) -> DiagnosticResult:
    family = "software" if any(term in payload.target_role.lower() for term in ("engineer", "developer", "software", "frontend", "backend")) else "data"
    expected_id = f"{family}-{payload.question_index}"
    if payload.question_id != expected_id:
        raise HTTPException(status_code=422, detail="Question id does not match the current diagnostic step.")
    if len(payload.history) != payload.question_index:
        raise HTTPException(status_code=422, detail="Diagnostic answer history is out of sequence.")
    if not 0 <= payload.selected_index < len(QUIZ_BANK[family][payload.question_index]["options"]):
        raise HTTPException(status_code=422, detail="Selected option is outside this question's answer choices.")
    result = grade_diagnostic(payload.target_role, payload.question_index, payload.selected_index, payload.history)
    return DiagnosticResult.model_validate(result)
