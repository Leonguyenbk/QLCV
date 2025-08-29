# app/models.py
from flask import app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Date, ForeignKey,
    Boolean, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SAEnum

from . import db
# dùng relative import, KHÔNG import create_app

# ==== Base ====
class BaseModel(db.Model):
    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True)

class OrgRole(PyEnum):
    MEMBER    = "Nhân viên"     # Tổ viên
    TEAM_LEAD = "Tổ trưởng"  # Tổ trưởng
    DEPT_HEAD = "Trưởng/ phó phòng"  # Trưởng/Phó phòng

class SystemRole(PyEnum):
    ADMIN = "ADMIN"               # Toàn quyền hệ thống
    HR_GENERAL = "HR_GENERAL"     # Quản lý nhân sự toàn cơ quan
    HR_DEPARTMENT = "HR_DEPARTMENT"  # Quản lý nhân sự trong phòng
    STAFF = "STAFF"      

class User(UserMixin, BaseModel):
    __tablename__ = 'users'
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(SystemRole), nullable=False, default=SystemRole.STAFF)
    employee_id = Column(Integer, ForeignKey('employees.id'), unique=True, nullable=True)

    @property
    def is_admin(self):
        """Kiểm tra người dùng có vai trò quản lý (Tổ trưởng, Trưởng phòng) hoặc là Admin hệ thống."""
        return self.role == SystemRole.ADMIN
    
    @property
    def is_hr_general(self):
        """Kiểm tra người dùng có vai trò HR General hay không."""
        return self.role == SystemRole.HR_GENERAL
    
    @property
    def is_hr_department(self):
        """Kiểm tra người dùng có vai trò HR Department hay không."""
        return self.role == SystemRole.HR_DEPARTMENT

    def can_manage(self, other_employee):
        """
        Kiểm tra xem người dùng hiện tại có quyền quản lý một nhân viên khác không.

        Quy tắc:
        - Admin có thể quản lý mọi người.
        - Trưởng phòng (DEPT_HEAD) có thể quản lý mọi nhân viên trong phòng của mình.
        - Tổ trưởng (TEAM_LEAD) có thể quản lý các Nhân viên (MEMBER) trong phòng của mình.
        - Người dùng không thể tự quản lý chính mình.
        """
        if not self.is_authenticated or not other_employee:
            return False

        # Admin có toàn quyền quản lý
        if self.role == SystemRole.ADMIN:
            return True

        # Nếu người dùng không phải là nhân viên, họ không thể quản lý ai (trừ Admin)
        if not self.employee:
            return False

        # Người dùng không thể tự quản lý chính mình
        if self.employee.id == other_employee.id:
            return False

        # Kiểm tra xem có cùng phòng ban không
        is_in_same_dept = self.employee.department_id and \
                          self.employee.department_id == other_employee.department_id

        if not is_in_same_dept:
            return False

        # Trưởng phòng có thể quản lý mọi người trong phòng
        if self.employee.org_role == OrgRole.DEPT_HEAD:
            return True

        # Tổ trưởng có thể quản lý các thành viên trong phòng
        if self.employee.org_role == OrgRole.TEAM_LEAD and other_employee.org_role == OrgRole.MEMBER:
            return True

        return False

# ==== Employee ====
class Employee(BaseModel):
    __tablename__ = 'employees'

    name = Column(String(100), nullable=False)
    year_of_birth = Column(DateTime)  # hoặc đổi sang Date nếu bạn chỉ cần ngày sinh
    position = Column(String(50), nullable=False)
    email = Column(String(100))
    phone = Column(String(15), nullable=True)
    avatar_url = Column(String(255), nullable=True)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=True)
    org_role = Column(SAEnum(OrgRole), nullable=False, default=OrgRole.MEMBER, index=True)
    user = db.relationship("User", backref="employee", uselist=False, cascade="all, delete")
    department = relationship('Department', back_populates='employees', lazy=True)

    job_details = relationship('JobDetail', back_populates='employee', lazy=True)
    @property
    def is_manager(self):
        """Kiểm tra người dùng có vai trò quản lý (Tổ trưởng, Trưởng phòng)"""
        return self.org_role == OrgRole.TEAM_LEAD or self.org_role == OrgRole.DEPT_HEAD

    # ✅ Quan hệ 1–n tới Absence dùng back_populates (đúng chuẩn)
    absences = relationship(
        'Absence',
        back_populates='employee',
        cascade='all, delete-orphan',
        lazy='selectin'
    )

    def __str__(self):
        return self.name

# ==== Department ====
class Department(BaseModel):
    __tablename__ = 'departments'

    name = Column(String(100), nullable=False, unique=True)

    # ✅ Quan hệ 1-n tới Employee dùng back_populates (đúng chuẩn)
    employees = relationship('Employee', back_populates='department', lazy=True)

    def __str__(self):
        return self.name

# ==== JobDetail ====
class JobDetail(BaseModel):
    __tablename__ = 'job_details'

    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    # ❗ default phải truyền callable, KHÔNG gọi hàm (không có ngoặc)
    date_posted = Column(DateTime, default=datetime.now)

    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    employee = relationship('Employee', back_populates='job_details', lazy=True)

    def __str__(self):
        return self.title

# ==== Absence (chuyên cần tối giản) ====
class AbsencePart(PyEnum):
    FULL = "Cả ngày"
    AM   = "Buổi sáng"
    PM   = "Buổi chiều"

class Absence(BaseModel):
    __tablename__ = 'absences'

    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False, index=True)

    # Dùng Date + default là callable date.today (mỗi lần insert lấy ngày hiện tại)
    work_date   = Column(Date, nullable=False, index=True, default=date.today)

    part = Column(SAEnum(AbsencePart), nullable=False, default=AbsencePart.FULL)
    is_permitted = Column(Boolean, nullable=False, default=False)
    reason = Column(String(200), nullable=True)

    employee = relationship('Employee', back_populates='absences', lazy='joined')

    __table_args__ = (
        UniqueConstraint('employee_id', 'work_date', 'part', name='uq_abs_employee_date_part'),
    )

    def __str__(self):
        label = "Có phép" if self.is_permitted else "Không phép"
        return f"{self.employee_id} - {self.work_date} - {self.part.value} - {label}"
    