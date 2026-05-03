"""Add statut_livraison to commandes

Revision ID: 20260504_0002
Revises: 20260504_0001
Create Date: 2026-05-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260504_0002"
down_revision: Union[str, Sequence[str], None] = "20260504_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "commandes",
        sa.Column(
            "statut_livraison",
            sa.String(length=50),
            nullable=False,
            server_default="non_assignee",
        ),
    )
    op.alter_column("commandes", "statut_livraison", server_default=None)


def downgrade() -> None:
    op.drop_column("commandes", "statut_livraison")
