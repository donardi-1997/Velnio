"""align paid plan pricing with public offer

Revision ID: 009_plan_pricing
Revises: 008_google_drive_oauth_state
Create Date: 2026-09-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "009_plan_pricing"
down_revision: Union[str, None] = "008_google_drive_oauth_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE plans
            SET name = CASE code
                    WHEN 'LAUNCH' THEN 'Starter'
                    ELSE name
                END,
                monthly_price = CASE code
                    WHEN 'LAUNCH' THEN 29
                    WHEN 'GROWTH' THEN 79
                    WHEN 'SCALE' THEN 149
                    ELSE monthly_price
                END
            WHERE code IN ('LAUNCH', 'GROWTH', 'SCALE')
            """
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE plans
            SET name = CASE code
                    WHEN 'LAUNCH' THEN 'Launch'
                    ELSE name
                END,
                monthly_price = CASE code
                    WHEN 'LAUNCH' THEN 19
                    WHEN 'GROWTH' THEN 49
                    WHEN 'SCALE' THEN 99
                    ELSE monthly_price
                END
            WHERE code IN ('LAUNCH', 'GROWTH', 'SCALE')
            """
        )
    )
