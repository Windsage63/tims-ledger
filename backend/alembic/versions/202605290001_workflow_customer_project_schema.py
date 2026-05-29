"""workflow customer and project schema alignment

Revision ID: 202605290001
Revises: 202605250001
Create Date: 2026-05-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202605290001"
down_revision: str | None = "202605250001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("billing_contact_name", sa.String(length=200), nullable=True))
    op.add_column("customers", sa.Column("billing_address_line1", sa.String(length=255), nullable=True))
    op.add_column("customers", sa.Column("billing_address_line2", sa.String(length=255), nullable=True))
    op.add_column("customers", sa.Column("billing_city", sa.String(length=120), nullable=True))
    op.add_column("customers", sa.Column("billing_state", sa.String(length=50), nullable=True))
    op.add_column("customers", sa.Column("billing_postal_code", sa.String(length=30), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE projects
            SET project_no = 'PRJ-' || printf('%04d', id)
            WHERE project_no IS NULL OR trim(project_no) = ''
            """
        )
    )

    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_index("ix_projects_project_no")
        batch_op.alter_column("project_no", existing_type=sa.String(length=80), nullable=False)
        batch_op.create_unique_constraint("uq_projects_project_no", ["project_no"])


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_constraint("uq_projects_project_no", type_="unique")
        batch_op.alter_column("project_no", existing_type=sa.String(length=80), nullable=True)
        batch_op.create_index("ix_projects_project_no", ["project_no"])

    op.drop_column("customers", "billing_postal_code")
    op.drop_column("customers", "billing_state")
    op.drop_column("customers", "billing_city")
    op.drop_column("customers", "billing_address_line2")
    op.drop_column("customers", "billing_address_line1")
    op.drop_column("customers", "billing_contact_name")