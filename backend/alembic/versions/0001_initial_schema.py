"""Initial database schema

Revision ID: 0001
Revises: 
Create Date: 2026-06-04
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── users ───────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("hashed_password", sa.String(256), nullable=False),
        sa.Column("full_name", sa.String(256), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="researcher"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_unique_constraint("uq_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_org_id", "users", ["org_id"])
    op.create_index("ix_users_is_active", "users", ["is_active"])

    # ─── projects ────────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("settings", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])
    op.create_index("ix_projects_org_id", "projects", ["org_id"])
    op.create_index("ix_projects_status", "projects", ["status"])

    # ─── research_jobs ────────────────────────────────────────────────────────
    op.create_table(
        "research_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("current_node", sa.String(64), nullable=True),
        sa.Column("completion_percent", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("orchestration_plan", postgresql.JSONB(), nullable=True),
        sa.Column("state_checkpoint", postgresql.JSONB(), nullable=True),
        sa.Column("quality_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("total_tokens_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_cost_usd", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("token_budget", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("human_review_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_rjobs_project_id", "research_jobs", ["project_id"])
    op.create_index("ix_rjobs_user_id", "research_jobs", ["user_id"])
    op.create_index("ix_rjobs_org_id", "research_jobs", ["org_id"])
    op.create_index("ix_rjobs_status", "research_jobs", ["status"])
    op.create_index("ix_rjobs_created_at", "research_jobs", ["created_at"])

    # ─── research_reports ─────────────────────────────────────────────────────
    op.create_table(
        "research_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("quality_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("citation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("citations", postgresql.JSONB(), nullable=True),
        sa.Column("key_findings", postgresql.JSONB(), nullable=True),
        sa.Column("recommendations", postgresql.JSONB(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_reports_job_id", "research_reports", ["job_id"])
    op.create_index("ix_reports_org_id", "research_reports", ["org_id"])
    op.create_index("ix_reports_status", "research_reports", ["status"])

    # ─── sources ─────────────────────────────────────────────────────────────
    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("content_preview", sa.Text(), nullable=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False, server_default="web"),
        sa.Column("tier", sa.SmallInteger(), nullable=False, server_default="2"),
        sa.Column("relevance_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("quality_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("authors", postgresql.JSONB(), nullable=True),
        sa.Column("year", sa.SmallInteger(), nullable=True),
        sa.Column("doi", sa.String(256), nullable=True),
        sa.Column("extra_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_sources_job_id", "sources", ["job_id"])
    op.create_index("ix_sources_org_id", "sources", ["org_id"])
    op.create_index("ix_sources_tier", "sources", ["tier"])

    # ─── agent_logs ──────────────────────────────────────────────────────────
    op.create_table(
        "agent_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_name", sa.String(64), nullable=False),
        sa.Column("model_id", sa.String(128), nullable=True),
        sa.Column("node_name", sa.String(64), nullable=True),
        sa.Column("level", sa.String(16), nullable=False, server_default="INFO"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(10, 8), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("is_fallback", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("quality_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_agent_logs_job_id", "agent_logs", ["job_id"])
    op.create_index("ix_agent_logs_org_id", "agent_logs", ["org_id"])
    op.create_index("ix_agent_logs_agent_name", "agent_logs", ["agent_name"])
    op.create_index("ix_agent_logs_level", "agent_logs", ["level"])
    op.create_index("ix_agent_logs_created_at", "agent_logs", ["created_at"])

    # updated_at auto-update trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    for table in ["users", "projects", "research_jobs", "research_reports", "sources"]:
        op.execute(f"""
            CREATE TRIGGER update_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade() -> None:
    for table in ["users", "projects", "research_jobs", "research_reports", "sources"]:
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column;")

    op.drop_table("agent_logs")
    op.drop_table("sources")
    op.drop_table("research_reports")
    op.drop_table("research_jobs")
    op.drop_table("projects")
    op.drop_table("users")
