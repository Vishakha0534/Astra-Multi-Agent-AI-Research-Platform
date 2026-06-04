"""Security tables: api_keys, user_sessions, audit_logs

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── api_keys ─────────────────────────────────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.String(512), nullable=True),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scopes", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"])
    op.create_index("ix_api_keys_is_active", "api_keys", ["is_active"])
    op.create_unique_constraint("uq_api_keys_hash", "api_keys", ["key_hash"])

    # ─── user_sessions ────────────────────────────────────────────────────────
    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("jti", sa.String(36), nullable=False, unique=True),
        sa.Column("refresh_token_hash", sa.String(64), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("device_name", sa.String(256), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_sessions_jti", "user_sessions", ["jti"])
    op.create_index("ix_sessions_is_active", "user_sessions", ["is_active"])

    # ─── audit_logs ───────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("event_outcome", sa.String(16), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.String(128), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_audit_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_org_id", "audit_logs", ["org_id"])
    op.create_index("ix_audit_event_type", "audit_logs", ["event_type"])
    op.create_index("ix_audit_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_ip_address", "audit_logs", ["ip_address"])

    # Extend trigger to new tables
    for table in ["api_keys", "user_sessions", "audit_logs"]:
        op.execute(f"""
            CREATE TRIGGER update_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade() -> None:
    for table in ["api_keys", "user_sessions", "audit_logs"]:
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};")
    op.drop_table("audit_logs")
    op.drop_table("user_sessions")
    op.drop_table("api_keys")
