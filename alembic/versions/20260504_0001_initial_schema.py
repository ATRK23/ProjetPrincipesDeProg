"""Initial schema

Revision ID: 20260504_0001
Revises:
Create Date: 2026-05-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260504_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("email", sa.String(length=150), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "livreurs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column("telephone", sa.String(length=30), nullable=True),
        sa.Column("moyen_transport", sa.String(length=50), nullable=True),
        sa.Column("note_moyenne", sa.Float(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_livreurs_id", "livreurs", ["id"], unique=False)

    op.create_table(
        "restaurants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("is_open", sa.Boolean(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_restaurants_id", "restaurants", ["id"], unique=False)

    op.create_table(
        "plats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column("prix", sa.Float(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ingredients", sa.Text(), nullable=True),
        sa.Column("allergenes", sa.Text(), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plats_id", "plats", ["id"], unique=False)

    op.create_table(
        "commandes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("livreur_id", sa.Integer(), nullable=True),
        sa.Column("statut", sa.String(length=50), nullable=False),
        sa.Column("prix_total", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["livreur_id"], ["livreurs.id"]),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commandes_id", "commandes", ["id"], unique=False)

    op.create_table(
        "commande_plat",
        sa.Column("commande_id", sa.Integer(), nullable=False),
        sa.Column("plat_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["commande_id"], ["commandes.id"]),
        sa.ForeignKeyConstraint(["plat_id"], ["plats.id"]),
        sa.PrimaryKeyConstraint("commande_id", "plat_id"),
    )


def downgrade() -> None:
    op.drop_table("commande_plat")
    op.drop_index("ix_commandes_id", table_name="commandes")
    op.drop_table("commandes")
    op.drop_index("ix_plats_id", table_name="plats")
    op.drop_table("plats")
    op.drop_index("ix_restaurants_id", table_name="restaurants")
    op.drop_table("restaurants")
    op.drop_index("ix_livreurs_id", table_name="livreurs")
    op.drop_table("livreurs")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
