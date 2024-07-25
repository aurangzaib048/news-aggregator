"""create aggregation_stats table

Revision ID: 9604c954b73b
Revises: 6c046672a695
Create Date: 2024-07-23 00:02:12.574069+00:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9604c954b73b"
down_revision = "6c046672a695"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'aggregation_stats',
        sa.Column('id', sa.UUID, primary_key=True),
        sa.Column('start_time', sa.DateTime, server_default=sa.func.now()),
        sa.Column('run_time', sa.BigInteger,  default=0),
        sa.Column('locale_name', sa.String, default=''),
        sa.Column('success', sa.Boolean, default=False),
        schema='news'
    )

    op.add_column('article', sa.Column('aggregation_id', sa.UUID, sa.ForeignKey('news.aggregation_stats.id'), nullable=True))
    op.add_column('article_cache_record', sa.Column('aggregation_id', sa.UUID, sa.ForeignKey('news.aggregation_stats.id'), nullable=True))


def downgrade():
    op.drop_column('article', 'aggregation_id', schema='news')
    op.drop_column('article_cache_record', 'aggregation_id', schema='news')
    op.drop_table('aggregation_stats', schema='news')
