"""Read-only access helpers for the HR team's Laravel-owned schema.

The AI service keeps its legacy SQLite/test models for local tests, but the
shared Railway database has a different, Laravel-owned schema.  This module
is the small compatibility boundary for that schema.  It never creates,
updates, or deletes HR records.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class SharedEmployee:
    """Employee identity exposed to the AI service using the public HR code."""

    id: str
    role_title: str
    department: str
    user_id: int


def is_shared_hr_schema(bind: Any) -> bool:
    """Return true only when the Laravel employee schema is present."""
    try:
        inspector = inspect(bind)
        tables = set(inspector.get_table_names())
        if not {"employees", "users", "departments"}.issubset(tables):
            return False
        employee_columns = {column["name"] for column in inspector.get_columns("employees")}
        return {"id", "employee_id", "user_id", "department_id"}.issubset(employee_columns)
    except (SQLAlchemyError, OSError):
        return False


def get_shared_employee(db: Session, external_id: str) -> SharedEmployee | None:
    """Resolve the public employee code against Laravel users/employees.

    The HR application can have a user before an optional row exists in
    ``employees``.  ``users.employee_id`` is also unique and is the identifier
    shown by the HR UI, so it is a valid fallback for authentication and
    employee-scoped reads.
    """
    row = db.execute(
        text("""
            SELECT COALESCE(e.employee_id, u.employee_id) AS employee_id,
                   COALESCE(e.job_title, u.job_title) AS job_title,
                   d.name AS department,
                   u.id AS user_id
            FROM users AS u
            LEFT JOIN employees AS e ON e.user_id = u.id AND e.deleted_at IS NULL
            LEFT JOIN departments AS d
              ON d.id = COALESCE(e.department_id, u.department_id)
             AND d.deleted_at IS NULL
            WHERE u.employee_id = :employee_id
              AND u.deleted_at IS NULL
            LIMIT 1
        """),
        {"employee_id": external_id.strip()},
    ).mappings().first()
    if row is None:
        return None
    return SharedEmployee(
        id=str(row["employee_id"]),
        role_title=str(row["job_title"] or ""),
        department=str(row["department"] or ""),
        user_id=int(row["user_id"]),
    )


def build_shared_career_context(
    db: Session,
    employee: SharedEmployee,
    period: str | None,
    limits: dict[str, int],
) -> dict[str, Any]:
    """Build a grounded context from existing Laravel HR records only."""
    period_like = None
    if period and "-Q" in period:
        year, quarter = period.split("-Q", 1)
        period_like = f"%Q{quarter} {year}%"

    params: dict[str, Any] = {
        "user_id": employee.user_id,
        "period_like": period_like,
    }
    period_filter = "AND (ep.name = :period OR ep.name LIKE :period_like)" if period else ""
    if period:
        params["period"] = period

    performance_rows = db.execute(
        text(f"""
            SELECT ev.id, ep.name AS period,
                   COALESCE(ev.overall_score, AVG(es.score)) AS overall_score,
                   ev.feedback
            FROM evaluations AS ev
            LEFT JOIN evaluation_periods AS ep ON ep.id = ev.period_id
            LEFT JOIN evaluation_scores AS es ON es.evaluation_id = ev.id
            WHERE ev.user_id = :user_id AND ev.status = 'completed' {period_filter}
            GROUP BY ev.id, ep.name, ev.overall_score, ev.feedback, ev.created_at
            ORDER BY ev.created_at DESC, ev.id DESC
            LIMIT {int(limits['performance'])}
        """),
        params,
    ).mappings().all()

    metric_row = db.execute(
        text("""
            SELECT
                (SELECT AVG(t.progress)
                 FROM task_assignments AS ta
                 INNER JOIN tasks AS t ON t.id = ta.task_id
                 WHERE ta.user_id = :user_id) AS task_completion_rate,
                (SELECT 100.0 * AVG(CASE WHEN g.status = 'completed' THEN 1 ELSE 0 END)
                 FROM goals AS g WHERE g.user_id = :user_id) AS goal_achievement_rate,
                (SELECT 100.0 * AVG(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END)
                 FROM attendances AS a WHERE a.user_id = :user_id) AS attendance_rate
        """),
        {"user_id": employee.user_id},
    ).mappings().one()

    goal_rows = db.execute(
        text(f"""
            SELECT g.id, g.title, g.description, g.status, g.target_date
            FROM goals AS g
            WHERE g.user_id = :user_id AND g.status IN ('active', 'completed')
            ORDER BY g.updated_at DESC, g.id DESC
            LIMIT {int(limits['goals'])}
        """),
        {"user_id": employee.user_id},
    ).mappings().all()

    task_rows = db.execute(
        text(f"""
            SELECT t.id, t.title, t.status, t.description, t.progress, t.deadline
            FROM task_assignments AS ta
            INNER JOIN tasks AS t ON t.id = ta.task_id
            WHERE ta.user_id = :user_id
            ORDER BY t.updated_at DESC, t.id DESC
            LIMIT {int(limits['task_outcomes'])}
        """),
        {"user_id": employee.user_id},
    ).mappings().all()

    theme_rows = db.execute(
        text(f"""
            SELECT es.id, ec.name AS theme, es.score, ev.feedback,
                   ep.name AS period, ee.description AS evidence
            FROM evaluation_scores AS es
            INNER JOIN evaluations AS ev ON ev.id = es.evaluation_id
            INNER JOIN evaluation_categories AS ec ON ec.id = es.category_id
            LEFT JOIN evaluation_periods AS ep ON ep.id = ev.period_id
            LEFT JOIN evaluation_evidence AS ee ON ee.evaluation_id = ev.id
            WHERE ev.user_id = :user_id AND ev.status = 'completed' {period_filter}
            ORDER BY ev.created_at DESC, es.id DESC
            LIMIT {int(limits['evaluation_themes'])}
        """),
        params,
    ).mappings().all()

    def normalize_period(value: Any) -> str:
        """Normalize Laravel labels such as '[TEST] Q4 2026 Review' to 2026-Q4."""
        raw = str(value or "").strip()
        match = re.search(r"Q([1-4])\s+(\d{4})", raw, re.IGNORECASE)
        return f"{match.group(2)}-Q{match.group(1)}" if match else raw

    normalized_performance = [
        {
            "id": int(row["id"]),
            "source_type": "performance",
            "period": normalize_period(row["period"]),
            "overall_score": float(row["overall_score"]),
            "task_completion_rate": float(metric_row["task_completion_rate"] or 0),
            "goal_achievement_rate": float(metric_row["goal_achievement_rate"] or 0),
            "attendance_rate": float(metric_row["attendance_rate"] or 0),
            "feedback": str(row["feedback"] or ""),
        }
        for row in performance_rows
        if row["overall_score"] is not None
    ]

    normalized_themes = [
        {
            "id": int(row["id"]),
            "source_type": "evaluation_theme",
            "theme": str(row["theme"] or ""),
            "sentiment": "",
            "evidence": str(row["evidence"] or row["feedback"] or ""),
            "period": normalize_period(row["period"]),
            "score": float(row["score"]),
        }
        for row in theme_rows
    ]

    context = {
        "employee": {
            "id": employee.id,
            "role_title": employee.role_title,
            "department": employee.department,
        },
        "performance": normalized_performance,
        "goals": [
            {
                "id": int(row["id"]),
                "source_type": "goal",
                "title": str(row["title"] or ""),
                "description": str(row["description"] or ""),
                "status": str(row["status"] or ""),
                "deadline": str(row["target_date"] or ""),
                "period": "",
            }
            for row in goal_rows
        ],
        # The Laravel schema has no standalone skills table. Evaluation
        # categories are the authoritative competency records, so expose the
        # same scored category rows as factual skill evidence.
        "skills": [
            {
                "id": item["id"],
                "source_type": "skill",
                "name": item["theme"],
                "level": f"score {item['score']}",
                "evidence": item["evidence"],
                "period": item["period"],
            }
            for item in normalized_themes
        ],
        "task_outcomes": [
            {
                "id": int(row["id"]),
                "source_type": "task_outcome",
                "title": str(row["title"] or ""),
                "status": str(row["status"] or ""),
                "outcome": str(row["description"] or ""),
                "completion_date": str(row["deadline"] or ""),
                "period": "",
                "progress": int(row["progress"] or 0),
            }
            for row in task_rows
        ],
        "evaluation_themes": normalized_themes,
    }
    missing = [category for category in ("performance", "goals", "skills", "task_outcomes", "evaluation_themes") if not context[category]]
    return {
        "has_sufficient_data": not missing,
        "missing_categories": missing,
        "context": context,
        "approved_sources": _approved_sources(context),
        "selected_source_ids": {
            category: [record["id"] for record in records]
            for category, records in context.items()
            if category != "employee"
        },
    }


def _approved_sources(context: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    return {
        (record["source_type"], record["id"]): record
        for category, records in context.items()
        if category != "employee"
        for record in records
    }
