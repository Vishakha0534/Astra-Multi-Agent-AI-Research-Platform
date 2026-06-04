from __future__ import annotations

from enum import Enum
from typing import ClassVar


class Permission(str, Enum):
    """All platform permissions. Format: action:resource."""

    # ─── User Management ──────────────────────────────────────────────────────
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    USER_MANAGE = "user:manage"            # Admin: deactivate, change roles

    # ─── Project ──────────────────────────────────────────────────────────────
    PROJECT_CREATE = "project:create"
    PROJECT_READ = "project:read"
    PROJECT_UPDATE = "project:update"
    PROJECT_DELETE = "project:delete"

    # ─── Research Jobs ────────────────────────────────────────────────────────
    JOB_CREATE = "job:create"
    JOB_READ = "job:read"
    JOB_CANCEL = "job:cancel"
    JOB_MANAGE = "job:manage"              # Admin: cancel any job

    # ─── Reports ──────────────────────────────────────────────────────────────
    REPORT_READ = "report:read"
    REPORT_WRITE = "report:write"
    REPORT_DELETE = "report:delete"
    REPORT_PUBLISH = "report:publish"

    # ─── Sources ──────────────────────────────────────────────────────────────
    SOURCE_READ = "source:read"
    SOURCE_WRITE = "source:write"

    # ─── Agent Logs ───────────────────────────────────────────────────────────
    AGENT_LOG_READ = "agent_log:read"
    AGENT_LOG_WRITE = "agent_log:write"

    # ─── API Keys ─────────────────────────────────────────────────────────────
    API_KEY_READ = "api_key:read"
    API_KEY_WRITE = "api_key:write"
    API_KEY_REVOKE = "api_key:revoke"

    # ─── Admin-only ───────────────────────────────────────────────────────────
    ADMIN_DASHBOARD = "admin:dashboard"
    AUDIT_LOG_READ = "audit_log:read"
    SYSTEM_CONFIG = "system:config"


# ─── Role → Permission matrix ────────────────────────────────────────────────

ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "admin": {
        # Full access — every permission
        Permission.USER_READ,
        Permission.USER_WRITE,
        Permission.USER_DELETE,
        Permission.USER_MANAGE,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_READ,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_DELETE,
        Permission.JOB_CREATE,
        Permission.JOB_READ,
        Permission.JOB_CANCEL,
        Permission.JOB_MANAGE,
        Permission.REPORT_READ,
        Permission.REPORT_WRITE,
        Permission.REPORT_DELETE,
        Permission.REPORT_PUBLISH,
        Permission.SOURCE_READ,
        Permission.SOURCE_WRITE,
        Permission.AGENT_LOG_READ,
        Permission.AGENT_LOG_WRITE,
        Permission.API_KEY_READ,
        Permission.API_KEY_WRITE,
        Permission.API_KEY_REVOKE,
        Permission.ADMIN_DASHBOARD,
        Permission.AUDIT_LOG_READ,
        Permission.SYSTEM_CONFIG,
    },
    "researcher": {
        Permission.USER_READ,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_READ,
        Permission.PROJECT_UPDATE,
        Permission.JOB_CREATE,
        Permission.JOB_READ,
        Permission.JOB_CANCEL,
        Permission.REPORT_READ,
        Permission.REPORT_WRITE,
        Permission.REPORT_PUBLISH,
        Permission.SOURCE_READ,
        Permission.SOURCE_WRITE,
        Permission.AGENT_LOG_READ,
        Permission.AGENT_LOG_WRITE,
        Permission.API_KEY_READ,
        Permission.API_KEY_WRITE,
    },
    "viewer": {
        Permission.USER_READ,
        Permission.PROJECT_READ,
        Permission.JOB_READ,
        Permission.REPORT_READ,
        Permission.SOURCE_READ,
        Permission.AGENT_LOG_READ,
        Permission.API_KEY_READ,
    },
}


class PermissionsEngine:
    """Evaluates whether a role holds a set of permissions."""

    @staticmethod
    def get_permissions(role: str) -> set[Permission]:
        """Return the full permission set for a given role."""
        return ROLE_PERMISSIONS.get(role, set())

    @staticmethod
    def has_permission(role: str, permission: Permission) -> bool:
        """Check if role holds a specific permission."""
        return permission in ROLE_PERMISSIONS.get(role, set())

    @staticmethod
    def has_any(role: str, *permissions: Permission) -> bool:
        """Return True if role holds ANY of the given permissions."""
        role_perms = ROLE_PERMISSIONS.get(role, set())
        return any(p in role_perms for p in permissions)

    @staticmethod
    def has_all(role: str, *permissions: Permission) -> bool:
        """Return True if role holds ALL of the given permissions."""
        role_perms = ROLE_PERMISSIONS.get(role, set())
        return all(p in role_perms for p in permissions)
