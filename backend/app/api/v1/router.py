from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, projects, research_jobs, reports, sources, agent_logs, health

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(research_jobs.router, prefix="/jobs", tags=["Research Jobs"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(sources.router, prefix="/sources", tags=["Sources"])
api_router.include_router(agent_logs.router, prefix="/agent-logs", tags=["Agent Logs"])
