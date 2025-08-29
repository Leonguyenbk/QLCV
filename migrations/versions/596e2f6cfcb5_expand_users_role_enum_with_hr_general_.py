"""Expand users.role enum with HR_GENERAL & HR_DEPARTMENT

Revision ID: 596e2f6cfcb5
Revises: 5313dc07c542
Create Date: 2025-08-29 13:57:27.484216

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '596e2f6cfcb5'
down_revision = '5313dc07c542'
branch_labels = None
depends_on = None

def upgrade():
    # Chuẩn hoá dữ liệu (phòng trường hợp có giá trị lạ/null)
    op.execute("""
        UPDATE `users`
        SET `role` = 'STAFF'
        WHERE `role` IS NULL
           OR `role` NOT IN ('ADMIN','HR_GENERAL','HR_DEPARTMENT','STAFF');
    """)
    # Thêm 2 giá trị mới vào ENUM và đặt default ở phía DB
    op.execute("""
        ALTER TABLE `users`
        MODIFY `role` ENUM('ADMIN','HR_GENERAL','HR_DEPARTMENT','STAFF')
        NOT NULL DEFAULT 'STAFF';
    """)

def downgrade():
    # Quay về ENUM cũ (nếu cần)
    op.execute("""
        UPDATE `users`
        SET `role` = 'STAFF'
        WHERE `role` NOT IN ('ADMIN','STAFF');
    """)
    op.execute("""
        ALTER TABLE `users`
        MODIFY `role` ENUM('ADMIN','STAFF')
        NOT NULL DEFAULT 'STAFF';
    """)
