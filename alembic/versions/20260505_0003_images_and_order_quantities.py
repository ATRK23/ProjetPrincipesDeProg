"""Add image URLs and order item quantities

Revision ID: 20260505_0003
Revises: 20260504_0002
Create Date: 2026-05-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260505_0003"
down_revision: Union[str, Sequence[str], None] = "20260504_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("restaurants", sa.Column("image_url", sa.String(length=255), nullable=True))
    op.add_column("plats", sa.Column("image_url", sa.String(length=255), nullable=True))
    op.add_column(
        "commande_plat",
        sa.Column("quantite", sa.Integer(), nullable=False, server_default="1"),
    )
    op.alter_column("commande_plat", "quantite", server_default=None)


def downgrade() -> None:
    op.drop_column("commande_plat", "quantite")
    op.drop_column("plats", "image_url")
    op.drop_column("restaurants", "image_url")
