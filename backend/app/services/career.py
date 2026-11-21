from __future__ import annotations

import asyncio
import ipaddress
import re
import ssl
import socket
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from backend.app.schemas import (
    AgentReport,
    ApplicationAnalysis,
    ApplicationRecord,
    ChallengeResult,
    ChallengeSubmission,
    DiagnosticQuestion,
    InterviewScore,
    MarketValue,
    PlanRequest,
    PlanResponse,
    PlanTask,
    ProjectBrief,
    ProjectRequest,
    ProjectResponse,
    SkillAnalysis,
    SkillEvidence,
    StackLayer,
)

SKILL_TERMS: dict[str, tuple[str, ...]] = {
    "SQL": ("sql", "postgres", "mysql", "bigquery"),
    "Python": ("python", "pandas"),
    "Data visualization": ("tableau", "power bi", "looker", "visualization", "dashboard"),
    "Statistics": ("statistics", "statistical", "probability", "hypothesis testing"),
    "Experimentation": ("experimentation", "a/b test", "ab test", "experiment design"),
    "Stakeholder communication": ("stakeholder", "executive communication", "cross-functional"),
    "dbt": ("dbt", "data modeling", "data models"),
    "Cloud data warehouse": ("snowflake", "redshift", "databricks", "data warehouse"),
    "Product analytics": ("product analytics", "funnel", "retention", "cohort analysis"),
    "Git": ("git", "github", "version control"),
    "JavaScript": ("javascript", "typescript", "react", "node.js"),
    "API design": ("rest api", "api design", "graphql"),
    "Testing": ("unit test", "integration test", "pytest", "jest"),
    "Accessibility": ("accessibility", "wcag", "aria"),
    "User research": ("user research", "usability testing", "interviews"),
    "SEO": ("seo", "search engine optimization", "keyword research"),
    "Campaign analytics": ("campaign analytics", "conversion rate", "attribution"),
    "Project management": ("project management", "agile", "scrum", "roadmap"),
    "Communication": ("communication", "presentations", "writing"),
}

QUIZ_BANK: dict[str, list[dict[str, object]]] = {
    "data": [
        {"skill": "SQL", "difficulty": "beginner", "prompt": "Which SQL clause filters rows before grouping?", "options": ["WHERE", "HAVING", "ORDER BY", "LIMIT"], "answer": 0, "why": "WHERE filters source rows before aggregation; HAVING filters grouped results."},
        {"skill": "Statistics", "difficulty": "beginner", "prompt": "What does a 95% confidence interval communicate?", "options": ["A range from a procedure that captures the true value in about 95% of repeated samples", "A 95% chance every observation is correct", "The largest possible sample mean", "Proof that a treatment caused an outcome"], "answer": 0, "why": "It describes long-run coverage of the interval procedure, not certainty about this one interval."},
        {"skill": "Product analytics", "difficulty": "intermediate", "prompt": "A signup funnel conversion fell. What is the best first check?", "options": ["Check instrumentation and compare the affected steps and segments", "Immediately redesign the whole signup flow", "Remove users who did not convert", "Compare only total monthly revenue"], "answer": 0, "why": "Validate tracking first, then localize the change by step, segment, and time."},
        {"skill": "Experimentation", "difficulty": "intermediate", "prompt": "Why define a primary metric before an experiment starts?", "options": ["To reduce selective interpretation and align on the decision", "To guarantee statistical significance", "To make every secondary metric improve", "To avoid measuring guardrails"], "answer": 0, "why": "A predeclared primary metric reduces cherry-picking and keeps the decision criterion clear."},
        {"skill": "SQL", "difficulty": "intermediate", "prompt": "How can you retain all customers while joining only matching purchases?", "options": ["LEFT JOIN", "INNER JOIN", "CROSS JOIN", "FULL JOIN followed by dropping nulls"], "answer": 0, "why": "A LEFT JOIN keeps every left-side customer and adds matching purchase fields."},
        {"skill": "Python", "difficulty": "intermediate", "prompt": "What is a useful first step when a DataFrame has unexpected duplicates?", "options": ["Inspect the intended row grain and duplicate keys before dropping rows", "Drop every repeated value", "Replace all nulls with zero", "Sort alphabetically"], "answer": 0, "why": "Understand the entity grain and keys before removing records to avoid deleting valid events."},
        {"skill": "Statistics", "difficulty": "advanced", "prompt": "A significant result appears after testing 40 metrics. What should you consider?", "options": ["Multiple comparisons and whether the metric was pre-specified", "Only the largest effect", "That every tested metric is causal", "Ignoring the sample size"], "answer": 0, "why": "Many tests raise false-positive risk; account for multiplicity and pre-specification."},
        {"skill": "Experimentation", "difficulty": "advanced", "prompt": "A randomized test has a sample-ratio mismatch. What should you do?", "options": ["Investigate assignment, logging, and eligibility before interpreting outcomes", "Ship the variant with the higher mean", "Exclude the smaller group", "Extend the test without investigating"], "answer": 0, "why": "A mismatch may signal assignment or instrumentation problems and can invalidate comparisons."},
        {"skill": "Data visualization", "difficulty": "beginner", "prompt": "Which chart is usually best for change over evenly spaced time?", "options": ["Line chart", "Pie chart", "Word cloud", "Treemap"], "answer": 0, "why": "A line chart communicates trends across an ordered time axis."},
        {"skill": "Stakeholder communication", "difficulty": "intermediate", "prompt": "A finding is directional but uncertain. How should you present it?", "options": ["State the estimate, uncertainty, limitations, and decision implication", "Hide uncertainty to sound confident", "Report only the p-value", "Promise the outcome will persist"], "answer": 0, "why": "Transparent uncertainty makes the evidence and its decision relevance usable."},
        {"skill": "Product analytics", "difficulty": "advanced", "prompt": "Why use a cohort view for retention?", "options": ["It compares groups by a shared starting event over elapsed time", "It removes all seasonality", "It proves feature causality", "It guarantees every user returns"], "answer": 0, "why": "Cohorts align users by a common start point, making lifecycle patterns easier to compare."},
        {"skill": "Cloud data warehouse", "difficulty": "intermediate", "prompt": "Why define a table's grain in an analytics model?", "options": ["To know what one row represents and prevent incorrect aggregation", "To reduce the number of columns", "To make the table confidential", "To avoid adding tests"], "answer": 0, "why": "A clear grain is essential for joining and aggregating without double counting."},
    ],
    "software": [
        {"skill": "JavaScript", "difficulty": "beginner", "prompt": "What does an HTTP 404 response normally mean?", "options": ["The requested resource was not found", "The server is healthy and request succeeded", "Authentication is required", "The server encountered an internal error"], "answer": 0, "why": "404 indicates the server could not find the requested resource."},
        {"skill": "API design", "difficulty": "beginner", "prompt": "Which HTTP method is conventionally used to retrieve a resource?", "options": ["GET", "POST", "DELETE", "PATCH"], "answer": 0, "why": "GET is used to retrieve a representation without requesting a state change."},
        {"skill": "Testing", "difficulty": "intermediate", "prompt": "What is the main purpose of a unit test?", "options": ["Check a small unit of behavior in isolation", "Prove the entire production system never fails", "Replace code review", "Test only the UI visually"], "answer": 0, "why": "Unit tests check focused behavior with controlled dependencies."},
        {"skill": "Git", "difficulty": "beginner", "prompt": "What does a Git commit represent?", "options": ["A recorded snapshot of project changes", "A deployment to production", "A package installation", "A running server process"], "answer": 0, "why": "A commit records a versioned snapshot and metadata in the repository history."},
        {"skill": "Accessibility", "difficulty": "intermediate", "prompt": "Why should an icon-only button have an accessible name?", "options": ["Assistive technologies need a meaningful control label", "It improves the image resolution", "It makes CSS load faster", "It prevents keyboard focus"], "answer": 0, "why": "A meaningful accessible name lets screen-reader users understand the control's purpose."},
        {"skill": "JavaScript", "difficulty": "intermediate", "prompt": "Why validate data on a server even if the browser validates it?", "options": ["Clients can be bypassed or modified", "Browser validation is always incorrect", "Server validation replaces authentication", "It removes the need for database constraints"], "answer": 0, "why": "Server-side validation is the trust boundary; client checks improve UX but are not security controls."},
        {"skill": "API design", "difficulty": "advanced", "prompt": "What makes retrying a request safer for a payment-like operation?", "options": ["An idempotency key that prevents duplicate effects", "A longer URL", "A browser cache", "Removing request validation"], "answer": 0, "why": "An idempotency key lets the server recognize retries of the same logical operation."},
        {"skill": "Testing", "difficulty": "advanced", "prompt": "What does a test double help with?", "options": ["Controlling or observing a dependency during a focused test", "Replacing production monitoring", "Compressing assets", "Authenticating end users"], "answer": 0, "why": "Mocks, fakes, and stubs isolate interactions for deterministic tests."},
        {"skill": "JavaScript", "difficulty": "intermediate", "prompt": "What is a common reason to use async/await?", "options": ["Write promise-based asynchronous flows in a readable sequence", "Make CPU-heavy work run on another machine automatically", "Skip error handling", "Turn JavaScript into SQL"], "answer": 0, "why": "async/await provides readable syntax for promises; errors still need handling."},
        {"skill": "Accessibility", "difficulty": "advanced", "prompt": "What should a modal dialog do with keyboard focus?", "options": ["Move focus inside, keep it contained, and restore it on close", "Remove focus from all controls", "Disable the Escape key unconditionally", "Hide its title from assistive technology"], "answer": 0, "why": "Managed focus keeps keyboard and assistive-tech navigation within the active dialog."},
        {"skill": "Git", "difficulty": "intermediate", "prompt": "Why review a diff before merging a change?", "options": ["To inspect the exact changes and catch unintended behavior", "To change the author's identity", "To remove test coverage", "To guarantee no production incident"], "answer": 0, "why": "Reviewing the diff helps spot accidental changes and assess the intended implementation."},
        {"skill": "API design", "difficulty": "advanced", "prompt": "What should a robust API do when a client sends invalid input?", "options": ["Return a clear client error without performing the operation", "Silently coerce every value", "Return success and ignore it", "Expose a stack trace and secrets"], "answer": 0, "why": "Validate at the boundary, return actionable errors, and avoid partial side effects."},
    ],
}


def _role_family(role: str) -> str:
    value = role.lower()
    if any(term in value for term in ("engineer", "developer", "software", "frontend", "backend")):
        return "software"
    return "data"


def next_diagnostic_question(role: str, history: list[dict[str, object]], index: int) -> DiagnosticQuestion:
    questions = QUIZ_BANK[_role_family(role)]
    base = questions[index % len(questions)]
    recent = history[-3:]
    recent_accuracy = sum(bool(item.get("correct")) for item in recent) / len(recent) if recent else 0.5
    difficulty = str(base["difficulty"])
    if recent_accuracy >= 0.75 and difficulty != "advanced":
        difficulty = "advanced" if difficulty == "intermediate" else "intermediate"
    elif recent_accuracy < 0.34 and difficulty != "beginner":
        difficulty = "beginner"
    return DiagnosticQuestion(
        id=f"{_role_family(role)}-{index}",
        skill=str(base["skill"]),
        difficulty=difficulty,  # type: ignore[arg-type]
        prompt=str(base["prompt"]),
        options=list(base["options"]),  # type: ignore[arg-type]
    )


def grade_diagnostic(role: str, index: int, selected: int, history: list[dict[str, object]]) -> dict[str, object]:
    question = QUIZ_BANK[_role_family(role)][index % 12]
    correct_index = int(question["answer"])
    is_correct = selected == correct_index
    next_history = [*history, {"correct": is_correct, "skill": question["skill"]}]
    correct_count = sum(bool(item.get("correct")) for item in next_history)
    result: dict[str, object] = {
        "correct": is_correct,
        "correct_index": correct_index,
        "explanation": str(question["why"]),
        "difficulty": next_diagnostic_question(role, history, index).difficulty,
        "score": round(correct_count / len(next_history) * 100),
        "completed": len(next_history) >= 12,
        "next_question": None,
    }
    if len(next_history) < 12:
        result["next_question"] = next_diagnostic_question(role, next_history, len(next_history))
    return result


def analyze_skills(role: str, resume: str, descriptions: list[str], quiz_scores: dict[str, int] | None = None) -> SkillAnalysis:
    frequencies: Counter[str] = Counter()
    for description in descriptions:
        text = description.lower()
        for skill, terms in SKILL_TERMS.items():
            if any(term in text for term in terms):
                frequencies[skill] += 1
    resume_text = resume.lower()
    quiz_scores = quiz_scores or {}
    skills: list[SkillEvidence] = []
    for skill, frequency in frequencies.most_common():
        present = any(term in resume_text for term in SKILL_TERMS[skill])
        quiz_score = quiz_scores.get(skill)
        status = "missing"
        if present and (quiz_score is None or quiz_score >= 75):
            status = "verified_strong" if quiz_score is not None else "needs_depth"
        elif present or (quiz_score is not None and quiz_score >= 40):
            status = "needs_depth"
        evidence = "Found in the supplied resume." if present else "No matching evidence found in the supplied resume."
        if quiz_score is not None:
            evidence += f" Diagnostic score: {quiz_score}%."
        skills.append(
            SkillEvidence(
                skill=skill,
                frequency=frequency,
                status=status,
                evidence=evidence,
                why_it_matters=f"Appears in {frequency} of {len(descriptions)} supplied job descriptions.",
                quiz_score=quiz_score,
            )
        )
    return SkillAnalysis(
        target_role=role,
        skills=skills,
        summary=f"Compared {len(descriptions)} job descriptions with the resume text provided. A quiz result is required to mark a skill verified strong.",
    )


SALARY_BANDS: dict[str, tuple[str, int, int]] = {
    "india": ("INR", 600_000, 1_400_000),
    "united states": ("USD", 55_000, 105_000),
    "usa": ("USD", 55_000, 105_000),
    "united kingdom": ("GBP", 32_000, 62_000),
    "uk": ("GBP", 32_000, 62_000),
    "canada": ("CAD", 55_000, 95_000),
    "germany": ("EUR", 42_000, 72_000),
    "australia": ("AUD", 65_000, 110_000),
}


def estimate_market_value(role: str, location: str, skills: list[str], projects: int, interview_score: int) -> MarketValue:
    currency, base_min, base_max = SALARY_BANDS.get(location.lower(), ("USD", 50_000, 95_000))
    role_lower = role.lower()
    if any(term in role_lower for term in ("senior", "lead", "staff")):
        base_min, base_max = int(base_min * 1.4), int(base_max * 1.65)
    elif any(term in role_lower for term in ("intern", "junior", "entry")):
        base_min, base_max = int(base_min * 0.72), int(base_max * 0.82)
    uplift = min(0.35, len(set(skills)) * 0.025 + min(projects, 4) * 0.025 + interview_score / 1000)
    factors = [
        f"{len(set(skills))} verified skill(s) considered",
        f"{projects} completed portfolio project(s) considered",
        f"Most recent interview score: {interview_score}/100",
        "Directional estimate only; verify with current local compensation sources.",
    ]
    return MarketValue(
        currency=currency,
        minimum=round(base_min * (1 + uplift)),
        maximum=round(base_max * (1 + uplift)),
        estimate_label="Illustrative annual range; not a salary survey or offer guarantee.",
        percentile=min(95, 35 + len(set(skills)) * 4 + min(projects, 4) * 3 + interview_score // 10),
        factors=factors,
    )


def build_learning_plan(request: PlanRequest, today: date | None = None) -> PlanResponse:
    today = today or date.today()
    target_date = request.target_date or (today + timedelta(days=84))
    target_days = max(1, (target_date - today).days)
    gaps = [item for item in request.skills if item.status != "verified_strong"]
    if not gaps:
        gaps = [SkillEvidence(skill="Role-specific portfolio proof", frequency=1, status="needs_depth")]
    gaps.sort(key=lambda item: (-item.frequency, item.status == "missing", item.skill))
    plans: list[PlanTask] = []
    for index, skill in enumerate(gaps):
        fundamentals_id = f"skill-{index + 1}-fundamentals"
        applied_id = f"skill-{index + 1}-applied"
        plans.append(
            PlanTask(
                id=fundamentals_id,
                week=index + 1,
                day=1,
                title=f"Learn the foundations of {skill.skill}",
                skill=skill.skill,
                estimated_hours=3.0,
            )
        )
        plans.append(
            PlanTask(
                id=applied_id,
                week=index + 1,
                day=3,
                title=f"Apply {skill.skill} to a role-relevant task",
                skill=skill.skill,
                estimated_hours=4.0,
                prerequisites=[fundamentals_id],
            )
        )
    if request.priority_mode:
        plans = plans[: max(2, min(len(plans), int(len(plans) * 0.4) or 2))]
    completed = set(request.completed_task_ids)
    estimated = sum(task.estimated_hours for task in plans)
    available = target_days * request.daily_study_hours
    required_daily = estimated / target_days
    feasible = estimated <= available
    warning = None if feasible else (
        f"Your plan needs about {required_daily:.1f} study hours/day by {target_date.isoformat()}, "
        f"but your current schedule provides {request.daily_study_hours:.1f}. "
        "Use 80/20 Priority Mode to focus on the highest-impact gaps."
    )
    tasks = [task.model_copy(update={"completed": task.id in completed}) for task in plans]
    rescheduled: list[str] = []
    for task in tasks:
        if task.completed:
            continue
        prerequisite_done = all(
            prerequisite in completed
            for prerequisite in task.prerequisites
        )
        if not prerequisite_done:
            continue
        due = today + timedelta(days=(task.week - 1) * 7 + task.day - 1)
        if due < today or due > target_date:
            rescheduled.append(task.id)
    return PlanResponse(
        tasks=tasks,
        target_days=target_days,
        available_hours=round(available, 1),
        estimated_hours_needed=round(estimated, 1),
        feasible=feasible,
        required_daily_hours=round(required_daily, 1),
        warning=warning,
        priority_mode=request.priority_mode,
        rescheduled_task_ids=rescheduled,
    )


def recommend_projects(request: ProjectRequest) -> ProjectResponse:
    missing = request.gaps or ["Role-specific technical skills", "Stakeholder communication"]
    first, second = missing[0], missing[1] if len(missing) > 1 else "Problem solving"
    projects = [
        ProjectBrief(
            title=f"{first} in a real-world workflow",
            problem=f"Build a focused case study that demonstrates {first} on a problem related to {request.target_role}.",
            bridge="Use the domain context in your existing background to make the solution useful rather than a generic tutorial.",
            tech_stack=[first, "Git", "README / project narrative"],
            milestones=["Define a testable problem and success measure", "Build the smallest useful working example", "Document trade-offs and what you would improve next"],
            interview_proof="Walk through the decisions, evidence, limitations, and the next iteration.",
        ),
        ProjectBrief(
            title=f"{second} decision brief",
            problem=f"Turn a small dataset, prototype, or user problem into an actionable recommendation for a {request.target_role} team.",
            bridge="Connect the project to a familiar audience or workflow from your prior experience.",
            tech_stack=[second, "Visualization or demo", "Decision memo"],
            milestones=["Choose a realistic question and gather evidence", "Create a clear analysis or prototype", "Present a recommendation with uncertainty and follow-up steps"],
            interview_proof="Show that you can explain the result to both a technical and a non-technical audience.",
        ),
    ]
    return ProjectResponse(projects=projects)


def application_insights(applications: list[ApplicationRecord]) -> ApplicationAnalysis:
    responded_status = {"interview", "offer", "rejected"}
    by_role: dict[str, list[bool]] = {}
    by_size: dict[str, list[bool]] = {}
    rejected_skills: Counter[str] = Counter()
    for application in applications:
        role_key = application.role_type or application.role_title
        size_key = application.company_size or "unspecified"
        response = application.status in responded_status
        by_role.setdefault(role_key, []).append(response)
        by_size.setdefault(size_key, []).append(response)
        if application.status == "rejected":
            rejected_skills.update(application.required_stack)
    callback = lambda group: {key: round(sum(values) / len(values) * 100, 1) for key, values in group.items()}
    response_rate = sum(app.status in responded_status for app in applications) / len(applications) * 100 if applications else 0
    recommendations = ["Track at least 5 outcomes per segment before treating a pattern as reliable."]
    if applications:
        best = max(by_role.items(), key=lambda item: sum(item[1]) / len(item[1]))
        recommendations.insert(0, f"Current strongest signal: {best[0]} ({sum(best[1])}/{len(best[1])} clear outcomes).")
    return ApplicationAnalysis(
        total=len(applications),
        response_rate=round(response_rate, 1),
        by_role_type=callback(by_role),
        by_company_size=callback(by_size),
        rejection_correlated_skills=[skill for skill, _ in rejected_skills.most_common(5)],
        recommendations=recommendations,
    )


def score_text_answer(answer: str, target_role: str, question: str, weak_skills: list[str]) -> InterviewScore:
    words = re.findall(r"\b[\w+#'-]+\b", answer)
    lower = answer.lower()
    structure = min(25, 10 + (7 if re.search(r"\b(first|then|because|result|outcome|finally|approach)\b", lower) else 0) + (5 if len(words) >= 45 else 0))
    evidence = bool(re.search(r"\b\d+%?|\b(reduced|increased|built|measured|tested|analyzed|analysed|validated)\b", lower))
    accuracy = min(25, 10 + (8 if evidence else 0) + (5 if len(words) >= 40 else 0))
    relevance = min(25, 10 + (10 if any(term in lower for term in target_role.lower().split() if len(term) > 3) else 0) + (5 if any(skill.lower() in lower for skill in weak_skills) else 0))
    clarity = min(25, max(5, 15 + (7 if 40 <= len(words) <= 180 else 0) - (5 if len(words) > 240 else 0)))
    scores = [accuracy, relevance, structure, clarity]
    weak = ["Technical accuracy", "Role relevance", "Structure", "Clarity"][scores.index(min(scores))]
    return InterviewScore(
        technical_accuracy=accuracy,
        depth=relevance,
        structure=structure,
        clarity=clarity,
        total=sum(scores),
        correction=f"Improve {weak.lower()} by answering: {question[:120]!r}. Name your method, evidence, and limitation; avoid claiming an outcome you cannot support.",
        follow_up="What evidence would change your recommendation, and how would you check it?",
        weak_topics=weak_skills[:3] or [weak],
    )


def score_challenge(submission: ChallengeSubmission) -> ChallengeResult:
    text = submission.submission.strip()
    words = re.findall(r"\b[\w+#'-]+\b", text)
    has_reasoning = bool(re.search(r"\b(because|therefore|trade-?off|assumption|approach|first|then)\b", text, re.I))
    has_evidence = bool(re.search(r"\b(test|result|example|measure|metric|validate|implement|analysis)\b", text, re.I))
    completeness = min(100, 25 + min(len(words), 150) // 3 + 15 * has_reasoning + 15 * has_evidence)
    score = int(completeness)
    return ChallengeResult(
        record_id=str(uuid4()),
        score=score,
        criteria={
            "technical_accuracy": min(100, 35 + 35 * has_evidence + 10 * has_reasoning),
            "problem_solving": min(100, 40 + 35 * has_reasoning + min(len(words), 100) // 5),
            "practicality": min(100, 30 + 40 * has_evidence + min(len(words), 100) // 5),
            "communication": min(100, 35 + min(len(words), 100) // 4 + 25 * has_reasoning),
        },
        strengths=["Submission was evaluated from the text provided."],
        improvements=[] if score >= 70 else ["Add a concrete example and explain the evidence behind your decisions."],
        feedback="Demo evaluation checks the submitted work for specificity, reasoning, and practical evidence. Connect Gemini for richer rubric feedback.",
        next_challenge=f"Extend the {submission.skill} example with a measurable outcome and one stated limitation.",
        submitted_at=datetime.now(timezone.utc),
    )


def build_agent_report(
    target_role: str,
    location: str,
    completed_tasks: int,
    upcoming_deadlines: list[str],
    missing_skills: list[str],
) -> AgentReport:
    opportunities = [
        {
            "title": f"Entry-level {target_role}",
            "organization": "Demo opportunity — replace with a configured job search source",
            "location": location,
            "match": max(35, 85 - 8 * len(missing_skills)),
            "why_match": f"Aligned to your target role; build evidence for {', '.join(missing_skills[:2]) or 'your strongest skills'}.",
            "source": "Seed data only; not a live vacancy",
            "requires_approval": False,
        }
    ]
    return AgentReport(
        generated_at=datetime.now(timezone.utc),
        opportunities=opportunities,
        reminders=upcoming_deadlines,
        progress_summary=f"{completed_tasks} learning task(s) completed so far.",
        portfolio_suggestions=[f"Add a concrete, reviewable {skill} deliverable to a portfolio project." for skill in missing_skills[:3]],
        weekly_focus=missing_skills[:3] or ["Practice a role-specific interview answer"],
        pending_approvals=[],
    )


async def inspect_public_project(raw_url: str, max_bytes: int = 1_000_000) -> dict[str, object]:
    parsed = urlparse(raw_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only public HTTPS URLs without embedded credentials can be inspected.")
    hostname = parsed.hostname.lower()
    if parsed.port not in (None, 443):
        raise ValueError("Only public HTTPS websites on the standard port can be inspected.")
    if hostname not in {"github.com", "www.github.com"}:
        addresses = _public_addresses(hostname)
        return await _fetch_public_https(raw_url, hostname, addresses, max_bytes)

    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        raise ValueError("Paste a GitHub repository URL in the form https://github.com/owner/repository.")
    owner, repo = parts[0], parts[1].removesuffix(".git")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", owner) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", repo):
        raise ValueError("The GitHub repository URL is malformed.")
    api_headers = {"Accept": "application/vnd.github+json", "User-Agent": "PivotPilot-ProjectScanner/1.0"}
    async with httpx.AsyncClient(timeout=8, follow_redirects=False, headers=api_headers) as client:
        response = await client.get(f"https://api.github.com/repos/{owner}/{repo}")
        if response.status_code == 404:
            raise ValueError("That repository is not public or could not be found.")
        response.raise_for_status()
        metadata = response.json()
        if metadata.get("private"):
            raise ValueError("Private repositories are not inspected.")
        branch = str(metadata.get("default_branch") or "main")
        manifests: dict[str, str] = {}
        for filename in ("package.json", "requirements.txt", "pyproject.toml", "go.mod", "Cargo.toml"):
            content_response = await client.get(f"https://api.github.com/repos/{owner}/{repo}/contents/{filename}", params={"ref": branch})
            if content_response.status_code == 200:
                content_data = content_response.json()
                encoded = content_data.get("content", "")
                if content_data.get("encoding") == "base64":
                    import base64

                    decoded = base64.b64decode(encoded, validate=False)[:max_bytes]
                    manifests[filename] = decoded.decode("utf-8", errors="replace")
        return {"url": raw_url, "repository": True, "title": str(metadata.get("description") or metadata.get("full_name") or repo), "language": metadata.get("language"), "topics": metadata.get("topics", []), "manifests": manifests}


def _public_addresses(hostname: str) -> list[str]:
    try:
        records = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise ValueError("The host could not be resolved.") from error
    addresses = {record[4][0] for record in records}
    if not addresses:
        raise ValueError("The host did not resolve to a public IP address.")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError("Only globally routable public websites can be inspected.")
    return sorted(addresses)


async def _fetch_public_https(raw_url: str, hostname: str, addresses: list[str], max_bytes: int) -> dict[str, object]:
    parsed = urlparse(raw_url)
    request_path = parsed.path or "/"
    if parsed.query:
        request_path += f"?{parsed.query}"
    ssl_context = ssl.create_default_context()
    last_error: Exception | None = None
    for address in addresses:
        writer: asyncio.StreamWriter | None = None
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(address, 443, ssl=ssl_context, server_hostname=hostname),
                timeout=5,
            )
            request = (
                f"GET {request_path} HTTP/1.1\r\n"
                f"Host: {hostname}\r\n"
                "User-Agent: PivotPilot-ProjectScanner/1.0\r\n"
                f"Range: bytes=0-{max_bytes - 1}\r\n"
                "Accept: text/html,text/plain;q=0.9,*/*;q=0.1\r\n"
                "Connection: close\r\n\r\n"
            )
            writer.write(request.encode("ascii"))
            await asyncio.wait_for(writer.drain(), timeout=5)
            headers = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5)
            if len(headers) > 65_536:
                raise ValueError("The website returned oversized response headers.")
            status_line, *header_lines = headers.decode("iso-8859-1").split("\r\n")
            status_parts = status_line.split(" ", 2)
            if len(status_parts) < 2 or not status_parts[1].isdigit():
                raise ValueError("The website returned an invalid HTTP response.")
            status_code = int(status_parts[1])
            response_headers: dict[str, str] = {}
            for line in header_lines:
                if ":" in line:
                    name, value = line.split(":", 1)
                    response_headers[name.lower().strip()] = value.strip()
            if 300 <= status_code < 400:
                raise ValueError("Redirected websites are not followed. Paste the final public HTTPS URL.")
            if status_code >= 400:
                raise ValueError(f"The website returned HTTP {status_code}.")
            length = response_headers.get("content-length")
            if length and int(length) > max_bytes:
                raise ValueError("The page is larger than the project's configured scan limit.")
            body = await asyncio.wait_for(reader.read(max_bytes + 1), timeout=5)
            if len(body) > max_bytes:
                body = body[:max_bytes]
            return {"url": raw_url, "repository": False, "title": body.decode("utf-8", errors="replace")[:2000], "headers": response_headers}
        except ValueError:
            raise
        except Exception as error:
            last_error = error
        finally:
            if writer:
                writer.close()
                try:
                    await writer.wait_closed()
                except OSError:
                    pass
    raise ValueError("The public website could not be reached safely.") from last_error


def infer_stack(scan: dict[str, object]) -> list[StackLayer]:
    layers: list[StackLayer] = []
    manifests = scan.get("manifests", {})
    package_text = str(manifests.get("package.json", "")).lower() if isinstance(manifests, dict) else ""
    requirements_text = " ".join(
        str(manifests.get(name, "")).lower()
        for name in ("requirements.txt", "pyproject.toml")
    ) if isinstance(manifests, dict) else ""
    if "react" in package_text or "next" in package_text or "vite" in package_text:
        layers.append(StackLayer(layer="Frontend", technologies=[item for item in ("React" if "react" in package_text else "", "Next.js" if "next" in package_text else "", "Vite" if "vite" in package_text else "") if item], evidence="Detected in package.json dependencies."))
    if "fastapi" in requirements_text or "django" in requirements_text or "flask" in requirements_text:
        layers.append(StackLayer(layer="Backend", technologies=[item for item in ("FastAPI" if "fastapi" in requirements_text else "", "Django" if "django" in requirements_text else "", "Flask" if "flask" in requirements_text else "") if item], evidence="Detected in Python dependency manifests."))
    if not layers and scan.get("language"):
        layers.append(StackLayer(layer="Repository language", technologies=[str(scan["language"])], evidence="Reported by GitHub repository metadata."))
    if not layers:
        layers.append(StackLayer(layer="Detection", technologies=["Not detected"], evidence="No supported manifest was found in the public repository root."))
    layers.append(StackLayer(layer="Auth / database / APIs", technologies=["Not verifiable from public root manifests alone"], evidence="Inspect source configuration and service policies manually; this scanner does not attempt to access private data."))
    return layers
