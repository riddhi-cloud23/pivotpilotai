from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.config import get_settings
from backend.app.schemas import ScannerRequest, ScannerResponse
from backend.app.security import require_user
from backend.app.services.career import infer_stack, inspect_public_project
from backend.app.services.gemini import generate_structured

router = APIRouter(prefix="/api/v1/scanner", tags=["project-scanner"])


class _ConceptResponse(BaseModel):
    concepts: list[str]
    learning_tasks: list[str]


@router.post("/analyze", response_model=ScannerResponse)
async def scan_project(payload: ScannerRequest, _user: str = Depends(require_user)) -> ScannerResponse:
    try:
        inspected = await inspect_public_project(str(payload.url), get_settings().max_scan_bytes)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail="The public project could not be inspected.") from error
    stack = infer_stack(inspected)
    prompt = (
        "From this public project metadata and dependency summary, identify concepts an early-career developer "
        "should learn to explain the architecture in an interview. Do not infer hidden or unobserved implementation. "
        f"Return concise JSON concepts and learning_tasks. Data: {inspected}. Stack: {[item.model_dump() for item in stack]}"
    )
    generated = await generate_structured(prompt, _ConceptResponse)
    concepts = generated.concepts if generated else ["Dependency management", "Request and data flow", "Testing and error handling", "Security boundaries"]
    tasks = generated.learning_tasks if generated else [f"Draw a diagram showing where {layer.technologies[0]} fits." for layer in stack[:3]]
    return ScannerResponse(
        url=str(payload.url),
        repository=bool(inspected.get("repository")),
        title=str(inspected.get("title", "")),
        stack=stack,
        concepts=concepts,
        learning_tasks=tasks,
        limitations=["Only public metadata and supported root manifests were inspected.", "The scan does not execute code or access private resources.", "Findings are a starting point, not a security audit."],
    )


@router.post("/inject-learning-plan")
def inject_concepts(concepts: list[str], _user: str = Depends(require_user)) -> dict[str, list[str]]:
    clean = [concept.strip()[:160] for concept in concepts[:20] if concept.strip()]
    return {"tasks_added": [f"Study and explain: {concept}" for concept in clean]}
