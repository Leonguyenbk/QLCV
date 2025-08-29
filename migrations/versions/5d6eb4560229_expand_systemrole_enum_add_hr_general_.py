"""Expand SystemRole enum: add HR_GENERAL & HR_DEPARTMENT

Revision ID: 5d6eb4560229
Revises: 596e2f6cfcb5
Create Date: 2025-08-29 14:09:25.650825

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5d6eb4560229'
down_revision = '596e2f6cfcb5'
branch_labels = None
depends_on = None

# Nếu có nhiều bảng/cột dùng SystemRole, liệt kê hết ở đây
TARGETS = [
    ("users", "role"),
    # ("another_table", "role"),  # thêm nếu có
]

NEW_ENUM = "ENUM('ADMIN','HR_GENERAL','HR_DEPARTMENT','STAFF')"
OLD_ENUM = "ENUM('ADMIN','STAFF')"

def upgrade():
    for table, col in TARGETS:
        op.execute(f"ALTER TABLE {table} MODIFY {col} {NEW_ENUM} NOT NULL")

def downgrade():
    # Cẩn thận: chỉ downgrade nếu dữ liệu hiện tại không chứa 2 giá trị mới
    for table, col in TARGETS:
        op.execute(f"ALTER TABLE {table} MODIFY {col} {OLD_ENUM} NOT NULL")
