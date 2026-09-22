"""phase 3a email data foundation"""

from alembic import op
import sqlalchemy as sa


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "email_message",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "source_record_id",
            sa.Integer(),
            sa.ForeignKey("source_record.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("normalized_message_id", sa.String(length=998), nullable=True),
        sa.Column("sender_address", sa.String(length=320), nullable=True),
        sa.Column("recipient_addresses", sa.Text(), nullable=True),
        sa.Column("subject", sa.String(length=998), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("in_reply_to", sa.String(length=998), nullable=True),
        sa.Column("references_header", sa.Text(), nullable=True),
        sa.Column("normalized_body", sa.Text(), nullable=True),
        sa.Column("body_size_bytes", sa.Integer(), nullable=True),
        sa.Column("content_truncated", sa.Boolean(), nullable=False),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "body_size_bytes IS NULL OR body_size_bytes >= 0",
            name="ck_email_message_body_size",
        ),
    )

    op.create_table(
        "imap_message_location",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "email_message_id",
            sa.Integer(),
            sa.ForeignKey("email_message.id"),
            nullable=False,
        ),
        sa.Column("account_scope", sa.String(length=100), nullable=False),
        sa.Column("folder_name", sa.String(length=255), nullable=False),
        sa.Column("uidvalidity", sa.Integer(), nullable=False),
        sa.Column("uid", sa.Integer(), nullable=False),
        sa.Column("location_state", sa.String(length=20), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "location_state IN ('active', 'unavailable')",
            name="ck_imap_message_location_state",
        ),
        sa.CheckConstraint(
            "uidvalidity >= 0",
            name="ck_imap_message_location_uidvalidity",
        ),
        sa.CheckConstraint("uid > 0", name="ck_imap_message_location_uid"),
        sa.UniqueConstraint(
            "account_scope",
            "folder_name",
            "uidvalidity",
            "uid",
            name="uq_imap_message_location_identity",
        ),
    )
    op.create_index(
        "ix_imap_message_location_lookup",
        "imap_message_location",
        ["account_scope", "folder_name", "uidvalidity", "uid"],
        unique=False,
    )

    op.create_table(
        "email_attachment_metadata",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "email_message_id",
            sa.Integer(),
            sa.ForeignKey("email_message.id"),
            nullable=False,
        ),
        sa.Column("part_index", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("media_type", sa.String(length=255), nullable=True),
        sa.Column("byte_size", sa.Integer(), nullable=True),
        sa.Column("content_id", sa.String(length=998), nullable=True),
        sa.Column("disposition", sa.String(length=100), nullable=True),
        sa.Column("provenance", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "part_index >= 0",
            name="ck_email_attachment_metadata_part_index",
        ),
        sa.CheckConstraint(
            "byte_size IS NULL OR byte_size >= 0",
            name="ck_email_attachment_metadata_byte_size",
        ),
        sa.UniqueConstraint(
            "email_message_id",
            "part_index",
            name="uq_email_attachment_metadata_part",
        ),
    )


def downgrade():
    op.drop_table("email_attachment_metadata")
    op.drop_index("ix_imap_message_location_lookup", table_name="imap_message_location")
    op.drop_table("imap_message_location")
    op.drop_table("email_message")
