from io import BytesIO
import re

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.app.config import get_settings
from backend.app.schemas import IntakeRequest, ParsedResume, SkillAnalysis
from backend.app.security import require_user
from backend.app.services.career import SKILL_TERMS, analyze_skills
from backend.app.services.gemini import generate_structured

router = APIRouter(tags=["intake-and-diagnostics"])


async def _extract_resume(content: bytes, filename: str) -> tuple[str, str]:
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix in {"txt", "md", "csv"}:
        return content.decode("utf-8-sig", errors="replace"), "text"
    if suffix == "pdf":
        try:
            import pdfplumber

            with pdfplumber.open(BytesIO(content)) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            return text, "pdf"
        except Exception as error:
            raise HTTPException(status_code=422, detail="The PDF could not be parsed. Try a text-based PDF or paste the resume.") from error
    if suffix == "docx":
        try:
            from docx import Document

            document = Document(BytesIO(content))
            return "\n".join(paragraph.text for paragraph in document.paragraphs), "docx"
        except Exception as error:
            raise HTTPException(status_code=422, detail="The DOCX could not be parsed. Try saving a new copy or paste the resume.") from error
    raise HTTPException(status_code=415, detail="Upload PDF, DOCX, TXT, Markdown, or CSV.")


@router.post("/api/v1/intake/parse", response_model=ParsedResume)
async def parse_resume(file: UploadFile = File(...), _user: str = Depends(require_user)) -> ParsedResume:
    settings = get_settings()
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail=f"Resume exceeds the {settings.max_upload_bytes // 1_000_000} MB upload limit.")
    text, source = await _extract_resume(content, file.filename or "")
    if len(text) > 60_000:
        text = text[:60_000]
    if not text.strip():
        raise HTTPException(status_code=422, detail="No readable resume text was found.")
    prompt = (
        "Extract a concise structured resume. Do not invent facts or metrics. "
        "Use only information present in the text. Return empty fields when absent.\n"
        f"RESUME:\n{text}"
    )
    parsed = await generate_structured(prompt, ParsedResume)
    if parsed:
        parsed.source = source  # type: ignore[assignment]
        parsed.extracted_text = text
        return parsed
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    lower = text.lower()
    skills = [skill for skill, terms in SKILL_TERMS.items() if any(term in lower for term in terms)]
    return ParsedResume(
        name=lines[0][:120] if lines else "",
        summary=next((line for line in lines[1:] if len(line) > 35), ""),
        extracted_text=text,
        skills=skills,
        experience_highlights=[line for line in lines if re.search(r"\b(built|led|improved|reduced|increased|managed|created|analyzed|analysed|partnered)\b", line, re.I)][:12],
        source=source,  # type: ignore[arg-type]
    )


@router.post("/api/v1/intake/validate", response_model=IntakeRequest)
def validate_intake(payload: IntakeRequest, _user: str = Depends(require_user)) -> IntakeRequest:
    if payload.start_date and payload.target_date and payload.target_date < payload.start_date:
        raise HTTPException(status_code=422, detail="Target end date must be on or after the target start date.")
    return payload


@router.post("/api/v1/skills/analyze", response_model=SkillAnalysis)
async def skill_analysis(payload: IntakeRequest, _user: str = Depends(require_user)) -> SkillAnalysis:
    if not payload.job_descriptions:
        raise HTTPException(status_code=422, detail="Add at least one target job description.")
    prompt = (
        "Compare resume evidence with requirements in the supplied job descriptions. "
        "Only mark verified_strong when the resume contains evidence; self-reported skills "
        "without examples should be needs_depth. Rank by JD frequency. Never invent credentials. "
        "Return the required JSON schema.\n"
        f"TARGET ROLE: {payload.target_role}\nRESUME:\n{payload.resume_text}\n"
        "JOB DESCRIPTIONS:\n" + "\n---\n".join(payload.job_descriptions)
    )
    generated = await generate_structured(prompt, SkillAnalysis)
    if generated:
        generated.target_role = payload.target_role
        generated.ai_generated = True
        return generated
    return analyze_skills(payload.target_role, payload.resume_text, payload.job_descriptions)
