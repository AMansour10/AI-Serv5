"""Database migration utility for adding `is_approved` column to HR tables.

Ensures idempotent, safe addition of `is_approved` column across:
- performance_records
- goals
- skills
- task_outcomes
- evaluation_themes

Backfill Policy:
- Legacy existing records default to `is_approved = False` (0) so they do NOT
  silently become approved.
- Newly created records default to `False` (0) unless explicitly approved by workflow.
"""

import logging
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

HR_TABLES_REQUIRING_IS_APPROVED = [
    "performance_records",
    "goals",
    "skills",
    "task_outcomes",
    "evaluation_themes",
]


def check_is_approved_columns(bind: Engine) -> dict[str, bool]:
    """Inspects the given engine/bind and returns whether `is_approved` column exists per table."""
    inspector = inspect(bind)
    existing_tables: set[str] = set(inspector.get_table_names())
    status: dict[str, bool] = {}

    for table_name in HR_TABLES_REQUIRING_IS_APPROVED:
        if table_name not in existing_tables:
            status[table_name] = False
            continue
        columns = [col["name"] for col in inspector.get_columns(table_name)]
        status[table_name] = "is_approved" in columns

    return status


def migrate_is_approved_columns(
    bind: Engine,
    default_for_legacy: bool = False,
) -> dict[str, Any]:
    """Safely and idempotently adds `is_approved` column to the 5 HR tables if missing.

    Parameters
    ----------
    bind : Engine
        SQLAlchemy engine for MySQL or SQLite.
    default_for_legacy : bool, default False
        Explicit backfill value for existing records.
        Per security policy: legacy rows must NOT silently become approved,
        so default_for_legacy defaults to False (0).

    Returns
    -------
    dict[str, Any]
        Migration report detailing added columns, existing columns, and backfill counts.
    """
    inspector = inspect(bind)
    existing_tables: set[str] = set(inspector.get_table_names())
    dialect_name: str = bind.dialect.name.lower()

    report: dict[str, Any] = {
        "dialect": dialect_name,
        "tables_checked": [],
        "columns_added": [],
        "already_present": [],
        "tables_missing": [],
        "backfill_default": default_for_legacy,
    }

    legacy_int_val = 1 if default_for_legacy else 0

    with bind.begin() as conn:
        for table_name in HR_TABLES_REQUIRING_IS_APPROVED:
            report["tables_checked"].append(table_name)

            if table_name not in existing_tables:
                report["tables_missing"].append(table_name)
                logger.info("Table '%s' does not exist yet. Skipping column migration.", table_name)
                continue

            columns = [col["name"] for col in inspector.get_columns(table_name)]
            if "is_approved" in columns:
                report["already_present"].append(table_name)
                logger.info("Column 'is_approved' already present in table '%s'.", table_name)
                continue

            # Column is missing: add it safely without destroying data
            logger.info("Adding 'is_approved' column to table '%s' (backfill: %s)...", table_name, default_for_legacy)
            if dialect_name in ("mysql", "mariadb"):
                alter_sql = text(
                    f"ALTER TABLE `{table_name}` "
                    f"ADD COLUMN `is_approved` TINYINT(1) NOT NULL DEFAULT {legacy_int_val}"
                )
            else:
                # SQLite / standard SQL
                alter_sql = text(
                    f"ALTER TABLE {table_name} "
                    f"ADD COLUMN is_approved BOOLEAN NOT NULL DEFAULT {legacy_int_val}"
                )

            conn.execute(alter_sql)
            report["columns_added"].append(table_name)

    return report

