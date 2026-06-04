from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.projects import router as projects_router
from app.api.v1.endpoints.research_jobs import router as research_jobs_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.sources import router as sources_router
from app.api.v1.endpoints.agent_logs import router as agent_logs_router

__all__ = [
    "health_router",
    "auth_router",
    "users_router",
    "projects_router",
    "research_jobs_router",
    "reports_router",
    "sources_router",
    "agent_logs_router",
]
