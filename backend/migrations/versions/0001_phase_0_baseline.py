"""Establish the initial schema migration baseline without domain tables.

Revision ID: 0001_phase_0_baseline
Revises:
Create Date: 2026-11-05
"""

from typing import Sequence

revision: str = "0001_phase_0_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
