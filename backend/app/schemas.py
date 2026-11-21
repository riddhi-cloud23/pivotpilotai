from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints
from typing_extensions import Annotated

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=60_000)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IntakeRequest(StrictModel):
    name: ShortText = "Career pivot"
    target_role: ShortText
    location: ShortText = "United States"
    start_date: date | None = None
    target_date: date | None = None
    daily_study_hours: float = Field(default=1, ge=0.25, le=16)
    resume_text: LongText = ""
    job_descriptions: list[LongText] = Field(default_factory=list, max_length=5)


class ParsedResume(StrictModel):
    name: str = ""
    summary: str = ""
    extracted_text: str = ""
    skills: list[str] = Field(default_factory=list)
    experience_highlights: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    source: Literal["pdf", "docx", "text"]


class SkillEvidence(StrictModel):
    skill: str
    frequency: int = Field(ge=0, le=5)
    status: Literal["verified_strong", "needs_depth", "missing"]
    evidence: str = ""
    why_it_matters: str = ""
    quiz_score: int | None = Field(default=None, ge=0, le=100)


class SkillAnalysis(StrictModel):
    target_role: str
    skills: list[SkillEvidence]
    summary: str
    ai_generated: bool = False


class DiagnosticQuestion(StrictModel):
    id: str
    skill: str
    difficulty: Literal["beginner", "intermediate", "advanced"]
    prompt: str
    options: list[str] = Field(min_length=2, max_length=6)


class DiagnosticAnswerRequest(StrictModel):
    target_role: ShortText
    question_index: int = Field(ge=0, le=11)
    question_id: ShortText
    selected_index: int = Field(ge=0, le=5)
    history: list[dict[str, Any]] = Field(default_factory=list, max_length=12)


class DiagnosticResult(StrictModel):
    correct: bool
    correct_index: int = Field(ge=0, le=5)
    explanation: str
    difficulty: Literal["beginner", "intermediate", "advanced"]
    score: int = Field(ge=0, le=100)
    completed: bool
    next_question: DiagnosticQuestion | None = None


class MarketValueRequest(StrictModel):
    target_role: ShortText
    location: ShortText = "United States"
    verified_skills: list[str] = Field(default_factory=list, max_length=50)
    completed_projects: int = Field(default=0, ge=0, le=100)
    interview_score: int = Field(default=0, ge=0, le=100)


class MarketValue(StrictModel):
    currency: str
    minimum: int
    maximum: int
    annual: bool = True
    estimate_label: str
    percentile: int
    factors: list[str]


class PlanRequest(StrictModel):
    target_role: ShortText
    target_date: date | None = None
    daily_study_hours: float = Field(default=1, ge=0.25, le=16)
    skills: list[SkillEvidence] = Field(default_factory=list, max_length=50)
    completed_task_ids: list[str] = Field(default_factory=list, max_length=500)
    priority_mode: bool = False


class PlanTask(StrictModel):
    id: str
    week: int = Field(ge=1)
    day: int = Field(ge=1, le=7)
    title: str
    skill: str
    estimated_hours: float = Field(gt=0, le=20)
    prerequisites: list[str] = Field(default_factory=list)
    completed: bool = False


class PlanResponse(StrictModel):
    tasks: list[PlanTask]
    target_days: int
    available_hours: float
    estimated_hours_needed: float
    feasible: bool
    required_daily_hours: float
    warning: str | None = None
    priority_mode: bool
    rescheduled_task_ids: list[str] = Field(default_factory=list)


class ProjectRequest(StrictModel):
    target_role: ShortText
    background: LongText = ""
    gaps: list[str] = Field(default_factory=list, max_length=30)


class ProjectBrief(StrictModel):
    title: str
    problem: str
    bridge: str
    tech_stack: list[str]
    milestones: list[str]
    interview_proof: str


class ProjectResponse(StrictModel):
    projects: list[ProjectBrief]
    ai_generated: bool = False


class MilestoneVerifyRequest(StrictModel):
    milestone_title: ShortText
    answers: list[str] = Field(min_length=3, max_length=3)


class MilestoneVerification(StrictModel):
    passed: bool
    score: int = Field(ge=0, le=100)
    feedback: list[str]


class BulletRequest(StrictModel):
    milestone_title: ShortText
    target_role: ShortText
    evidence: LongText


class BulletResponse(StrictModel):
    bullets: list[str]
    ai_generated: bool = False


class InterviewRequest(StrictModel):
    target_role: ShortText
    weak_skills: list[str] = Field(default_factory=list, max_length=20)
    answer: LongText = ""
    question: str = ""


class InterviewQuestionResponse(StrictModel):
    question: str
    source_note: str


class InterviewScore(StrictModel):
    technical_accuracy: int = Field(ge=0, le=25)
    depth: int = Field(ge=0, le=25)
    structure: int = Field(ge=0, le=25)
    clarity: int = Field(ge=0, le=25)
    total: int = Field(ge=0, le=100)
    correction: str
    follow_up: str
    weak_topics: list[str]
    ai_generated: bool = False


class ApplicationRecord(StrictModel):
    role_title: ShortText
    role_type: str = ""
    company: ShortText
    company_size: str = ""
    company_type: str = ""
    work_mode: Literal["remote", "hybrid", "onsite", "unspecified"] = "unspecified"
    required_stack: list[str] = Field(default_factory=list, max_length=50)
    resume_version: str = ""
    status: Literal["applied", "ghosted", "rejected", "interview", "offer"] = "applied"
    applied_at: datetime | None = None
    deadline: datetime | None = None
    notes: str = ""


class ApplicationAnalysis(StrictModel):
    total: int
    response_rate: float
    by_role_type: dict[str, float]
    by_company_size: dict[str, float]
    rejection_correlated_skills: list[str]
    recommendations: list[str]


class ScannerRequest(StrictModel):
    url: HttpUrl


class StackLayer(StrictModel):
    layer: str
    technologies: list[str]
    evidence: str


class ScannerResponse(StrictModel):
    url: str
    repository: bool
    title: str = ""
    stack: list[StackLayer]
    concepts: list[str]
    learning_tasks: list[str]
    limitations: list[str]


class ChallengeRequest(StrictModel):
    target_role: ShortText
    skill: ShortText
    difficulty: Literal["beginner", "intermediate", "advanced"] = "beginner"
    domain: str = "general"


class ChallengeBrief(StrictModel):
    challenge_id: str
    title: str
    skill: str
    difficulty: Literal["beginner", "intermediate", "advanced"]
    scenario: str
    instructions: list[str]
    time_limit_minutes: int = Field(ge=5, le=240)
    evaluation_criteria: list[str]


class ChallengeSubmission(StrictModel):
    challenge_id: ShortText
    title: ShortText
    skill: ShortText
    difficulty: Literal["beginner", "intermediate", "advanced"]
    instructions: LongText
    submission: LongText


class ChallengeResult(StrictModel):
    record_id: str
    score: int = Field(ge=0, le=100)
    criteria: dict[str, int]
    strengths: list[str]
    improvements: list[str]
    feedback: str
    next_challenge: str
    submitted_at: datetime
    ai_generated: bool = False


class OpportunityPreferences(StrictModel):
    target_role: ShortText
    location: ShortText = "Remote"
    remote_only: bool = False
    include_internships: bool = True


class AgentReport(StrictModel):
    generated_at: datetime
    opportunities: list[dict[str, Any]]
    reminders: list[str]
    progress_summary: str
    portfolio_suggestions: list[str]
    weekly_focus: list[str]
    pending_approvals: list[dict[str, Any]]
    ai_generated: bool = False
