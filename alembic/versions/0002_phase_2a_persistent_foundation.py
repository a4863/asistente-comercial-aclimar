"""phase 2a persistent foundation"""
from alembic import op
from app.persistence.models import Base

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

def upgrade():
    Base.metadata.create_all(bind=op.get_bind())

def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())
