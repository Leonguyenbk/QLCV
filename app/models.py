# Tạo cơ sở dũ liệu nhân sự và bảng chi tiết công việc
from sqlalchemy import *
from sqlalchemy.orm import relationship
from datetime import datetime
from app import db, create_app
from enum import Enum as UserEnum

class BaseModel(db.Model):
    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True)

class Employee(BaseModel):
    __tablename__ = 'employees'

    name = Column(String(100), nullable=False)
    year_of_birth = Column(DateTime)
    position = Column(String(50), nullable=False)
    email = Column(String(100))
    phone = Column(String(15), nullable=True)
    job_details = relationship('JobDetail', back_populates='employee', lazy=True)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=True)
    department = relationship('Department', backref='employees', lazy=True)

    def __str__(self):
        return self.name

#Tạo bảng tổ chuyên môn
class Department(BaseModel):
    __tablename__ = 'departments'

    name = Column(String(100), nullable=False, unique=True)

    def __str__(self):
        return self.name

class JobDetail(BaseModel):
    __tablename__ = 'job_details'

    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    date_posted = Column(DateTime, default=datetime.now())
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    employee = relationship('Employee', back_populates='job_details', lazy=True)

    def __str__(self):
        return self.title