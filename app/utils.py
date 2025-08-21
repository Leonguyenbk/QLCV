from app import create_app, db
from app.models import Employee
from flask import current_app


def load_employees(employee_id=None, kw=None, department_id=None, page=1):
    query = Employee.query

    if employee_id:
        query = query.filter(Employee.id == employee_id)

    if kw:
        kw = kw.strip()
        if kw:
            query = query.filter(Employee.name.ilike(f"%{kw}%"))

    if department_id:
        query = query.filter(Employee.department_id == department_id)

    query = query.order_by(Employee.id.asc())
    page_size = current_app.config['PAGE_SIZE']
    start = (page - 1)*page_size
    end = page_size + start
    return query.slice(start, end).all()

def get_employee_by_id(employee_id):
    return Employee.query.get(employee_id)

def count_employees():
    return Employee.query.order_by(None).count()