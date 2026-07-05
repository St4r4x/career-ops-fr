"""Add user profile, settings, and CV tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-05
"""

from __future__ import annotations
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.Text, primary_key=True),
        sa.Column("name", sa.Text, nullable=False, server_default=""),
        sa.Column("title", sa.Text, nullable=False, server_default=""),
        sa.Column("email", sa.Text, nullable=False, server_default=""),
        sa.Column("phone", sa.Text, nullable=False, server_default=""),
        sa.Column("location", sa.Text, nullable=False, server_default=""),
        sa.Column("linkedin", sa.Text, nullable=False, server_default=""),
        sa.Column("github", sa.Text, nullable=False, server_default=""),
        sa.Column("profile_md", sa.Text, nullable=False, server_default=""),
    )
    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.Text, primary_key=True),
        sa.Column("keywords", sa.ARRAY(sa.Text), nullable=False, server_default="{}"),
        sa.Column(
            "portal_queries", sa.ARRAY(sa.Text), nullable=False, server_default="{}"
        ),
        sa.Column("location", sa.Text, nullable=False, server_default=""),
        sa.Column("contract", sa.Text, nullable=False, server_default="CDI"),
        sa.Column(
            "experience_max_years", sa.Integer, nullable=False, server_default="3"
        ),
        sa.Column("salary_min", sa.Integer, nullable=False, server_default="0"),
        sa.Column("salary_max", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "target_companies", sa.ARRAY(sa.Text), nullable=False, server_default="{}"
        ),
        sa.Column("follow_up_days", sa.Integer, nullable=False, server_default="7"),
    )
    op.create_table(
        "user_ats_targets",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("careers_url", sa.Text, nullable=False),
    )
    op.create_index("ix_user_ats_targets_user", "user_ats_targets", ["user_id"])
    op.create_table(
        "user_cv_meta",
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("lang", sa.Text, nullable=False),
        sa.Column("summary", sa.Text, nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("user_id", "lang"),
    )
    op.create_table(
        "user_experience",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("lang", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=False, server_default=""),
        sa.Column("company", sa.Text, nullable=False, server_default=""),
        sa.Column("type", sa.Text, nullable=False, server_default=""),
        sa.Column("period", sa.Text, nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_user_experience_user_lang", "user_experience", ["user_id", "lang"]
    )
    op.create_table(
        "user_experience_bullets",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "experience_id",
            sa.Integer,
            sa.ForeignKey("user_experience.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text, nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_table(
        "user_skills",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("lang", sa.Text, nullable=False),
        sa.Column("category", sa.Text, nullable=False),
        sa.Column("skill", sa.Text, nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index("ix_user_skills_user_lang", "user_skills", ["user_id", "lang"])
    op.create_table(
        "user_certifications",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("issuer", sa.Text, nullable=False, server_default=""),
        sa.Column("year", sa.Integer, nullable=True),
    )
    op.create_table(
        "user_education",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("lang", sa.Text, nullable=False),
        sa.Column("degree", sa.Text, nullable=False, server_default=""),
        sa.Column("school", sa.Text, nullable=False, server_default=""),
        sa.Column("year", sa.Integer, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("user_education")
    op.drop_table("user_certifications")
    op.drop_table("user_skills")
    op.drop_table("user_experience_bullets")
    op.drop_table("user_experience")
    op.drop_table("user_cv_meta")
    op.drop_index("ix_user_ats_targets_user")
    op.drop_table("user_ats_targets")
    op.drop_table("user_settings")
    op.drop_table("user_profiles")
