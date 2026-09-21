import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root is in sys.path when executed directly
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv()

import logging

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

import app.models
from app.api.attention_signal import router as attention_signal_router
from app.api.career_coach import router as career_coach_router
from app.api.evaluation_draft import router as evaluation_draft_router
from app.api.health import router as health_router
from app.api.insight_snapshots import router as insight_snapshots_router
from app.api.performance_insight import router as performance_insight_router
from app.api.policy_assistant import router as policy_assistant_router
from app.api.skill_gap import router as skill_gap_router
from app.api.team_insight import router as team_insight_router
from app.db.migrations import (
    migrate_ai_audit_events_table,
    migrate_ai_snapshots_tables,
    migrate_chat_message_embedding_column,
    migrate_is_approved_columns,
)
from app.db.session import DB_CONFIG_ERROR, Base, engine, get_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # When dependency overrides are active (e.g. in test suites), allow caller to manage test database
    if get_db in app.dependency_overrides:
        app.state.db_initialized = True
        app.state.db_initialization_error = None
        yield
        return

    if DB_CONFIG_ERROR is not None:
        logger.warning("Database configuration error at startup: %s", DB_CONFIG_ERROR)
        app.state.db_initialization_error = "database_configuration_invalid"
        app.state.db_initialized = False
        yield
        return

    app.state.db_initialized = False
    app.state.db_initialization_error = None
    # Initialize database schema and ensure idempotent column migrations at startup
    try:
        Base.metadata.create_all(bind=engine)
        migrate_is_approved_columns(bind=engine, default_for_legacy=False)
        migrate_chat_message_embedding_column(bind=engine)
        migrate_ai_audit_events_table(bind=engine)
        migrate_ai_snapshots_tables(bind=engine)
        app.state.db_initialized = True
    except (SQLAlchemyError, OSError) as exc:
        logger.warning("Database schema initialization warning: %s", exc)
        app.state.db_initialization_error = str(exc)
        app.state.db_initialized = False
    yield


app = FastAPI(
    title="Smart HR Management System - AI Service",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.db_initialized = False
app.state.db_initialization_error = None

# Register Health and API Routers
app.include_router(health_router)
app.include_router(health_router, prefix="/api")
app.include_router(career_coach_router, prefix="/api")
app.include_router(performance_insight_router, prefix="/api")
app.include_router(policy_assistant_router, prefix="/api")
app.include_router(evaluation_draft_router, prefix="/api")
app.include_router(skill_gap_router, prefix="/api")
app.include_router(attention_signal_router, prefix="/api")
app.include_router(team_insight_router, prefix="/api")
app.include_router(insight_snapshots_router, prefix="/api/insights")
app.include_router(insight_snapshots_router, prefix="/insights", include_in_schema=False)



@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "Smart HR Management System - AI Service"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)


