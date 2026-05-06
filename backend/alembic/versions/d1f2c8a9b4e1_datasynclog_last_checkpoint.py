"""DataSyncLog last_checkpoint (chunk-level resume 정확도)

Revision ID: d1f2c8a9b4e1
Revises: c0827aa6f216
Create Date: 2026-05-06 17:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = 'd1f2c8a9b4e1'
down_revision: Union[str, None] = 'c0827aa6f216'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('data_sync_logs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_checkpoint', sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('data_sync_logs', schema=None) as batch_op:
        batch_op.drop_column('last_checkpoint')
