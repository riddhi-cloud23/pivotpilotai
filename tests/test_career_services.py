from datetime import date, timedelta

from backend.app.schemas import ApplicationRecord, PlanRequest, SkillEvidence
from backend.app.services.career import (
    analyze_skills,
    application_insights,
    build_learning_plan,
    estimate_market_value,
    grade_diagnostic,
    next_diagnostic_question,
)


def test_skill_analysis_ranks_frequency_and_requires_quiz_for_verified() -> None:
    result = analyze_skills(
        "Product Analyst",
        "Used SQL to report customer trends.",
        ["SQL, Tableau, experiments", "SQL and Python"],
    )
    assert result.skills[0].skill == "SQL"
    assert result.skills[0].frequency == 2
    assert result.skills[0].status == "needs_depth"
    assert next(item for item in result.skills if item.skill == "Python").status == "missing"


def test_diagnostic_returns_twelve_steps_and_adapts() -> None:
    first = next_diagnostic_question("Data Analyst", [], 0)
    history = [{"correct": True} for _ in range(3)]
    adaptive = next_diagnostic_question("Data Analyst", history, 3)
    assert first.id == "data-0"
    assert adaptive.difficulty == "advanced"
    outcome = grade_diagnostic("Data Analyst", 0, 0, [])
    assert outcome["correct"] is True
    assert outcome["score"] == 100


def test_planner_explains_infeasible_deadline_and_preserves_prerequisites() -> None:
    skills = [
        SkillEvidence(skill="SQL", frequency=3, status="missing"),
        SkillEvidence(skill="Python", frequency=2, status="needs_depth"),
    ]
    plan = build_learning_plan(
        PlanRequest(
            target_role="Data Analyst",
            target_date=date.today() + timedelta(days=2),
            daily_study_hours=1,
            skills=skills,
        )
    )
    assert not plan.feasible
    assert plan.required_daily_hours > 1
    applied = next(task for task in plan.tasks if "Apply SQL" in task.title)
    assert applied.prerequisites == ["skill-1-fundamentals"]


def test_market_value_is_regional_and_changes_with_proof() -> None:
    base = estimate_market_value("Data Analyst", "India", [], 0, 0)
    improved = estimate_market_value("Data Analyst", "India", ["SQL", "Python"], 2, 80)
    assert base.currency == "INR"
    assert improved.minimum > base.minimum
    assert improved.maximum > base.maximum


def test_application_analysis_calculates_outcome_patterns() -> None:
    records = [
        ApplicationRecord(role_title="Analyst", role_type="Product", company="A", company_size="Startup", status="interview"),
        ApplicationRecord(role_title="Analyst", role_type="Product", company="B", company_size="Startup", status="rejected", required_stack=["Python"]),
        ApplicationRecord(role_title="Analyst", role_type="BI", company="C", company_size="Large", status="applied"),
    ]
    result = application_insights(records)
    assert result.total == 3
    assert result.response_rate == 66.7
    assert result.by_role_type["Product"] == 100.0
    assert "Python" in result.rejection_correlated_skills
