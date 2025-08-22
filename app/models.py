# app/models.py
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

from . import db  # dùng relative import, KHÔNG import create_app

# ==== Base ====
class BaseModel(db.Model):
    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True)

class OrgRole(PyEnum):
    MEMBER    = "Nhân viên"     # Tổ viên
    TEAM_LEAD = "Tổ trưởng"  # Tổ trưởng
    DEPT_HEAD = "Trưởng/ phó phòng"  # Trưởng/Phó phòng

class SystemRole(PyEnum):
    ADMIN = "ADMIN"
    STAFF = "STAFF"

class User(UserMixin, BaseModel):
    __tablename__ = 'users'
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(SystemRole), nullable=False, default=SystemRole.STAFF)
    employee_id = Column(Integer, ForeignKey('employees.id'), unique=True, nullable=True)

    employee = relationship('Employee', backref='user', lazy='joined')

# ==== Employee ====
class Employee(BaseModel):
    __tablename__ = 'employees'

    name = Column(String(100), nullable=False)
    year_of_birth = Column(DateTime)  # hoặc đổi sang Date nếu bạn chỉ cần ngày sinh
    position = Column(String(50), nullable=False)
    email = Column(String(100))
    phone = Column(String(15), nullable=True)

    department_id = Column(Integer, ForeignKey('departments.id'), nullable=True)
    org_role = Column(SAEnum(OrgRole), nullable=False, default=OrgRole.MEMBER, index=True)
    department = relationship('Department', back_populates='employees', lazy=True)

    job_details = relationship('JobDetail', back_populates='employee', lazy=True)

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
