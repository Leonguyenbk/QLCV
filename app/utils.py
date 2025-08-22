from app import create_app, db
from app.models import Employee, Absence, AbsencePart, User, SystemRole
from flask import current_app
from calendar import monthrange
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
import re

def get_user_by_id(user_id):
    return User.query.get(user_id)

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

def check_login(username: str, password: str):
    user = User.query.filter(User.username == username.strip()).first()
    if not user:
        return None
    if check_password_hash(user.password_hash, password.strip()):
        return user
    return None

def get_employee_by_id(employee_id):
    return Employee.query.get(employee_id)

def count_employees():
    return Employee.query.order_by(None).count()

def parse_month(month_str: str | None):
    """Nhận 'mm-yyyy' hoặc 'yyyy-mm' -> (year, month). Sai/thiếu -> tháng hiện tại."""
    today = date.today()
    if not month_str:
        return today.year, today.month
    s = month_str.strip()
    m1 = re.match(r'^(0[1-9]|1[0-2])-(\d{4})$', s)          # mm-yyyy
    if m1:
        return int(m1.group(2)), int(m1.group(1))
    m2 = re.match(r'^(\d{4})-(0[1-9]|1[0-2])$', s)          # yyyy-mm (fallback)
    if m2:
        return int(m2.group(1)), int(m2.group(2))
    return today.year, today.month

def absence_summary(session, employee_id: int, year: int, month: int):
    start_day = date(year, month, 1)
    end_day = date(year, month, monthrange(year, month)[1])

    q = (session.query(Absence)
         .filter(Absence.employee_id == employee_id,
                 Absence.work_date >= start_day,
                 Absence.work_date <= end_day))

    total = permitted = unpermitted = 0.0

    for a in q.all():
        val = 1.0 if a.part == AbsencePart.FULL else 0.5
        total += val
        if a.is_permitted:
            permitted += val
        else:
            unpermitted += val

    return {
        "total_days_off": total,
        "permitted_days_off": permitted,
        "unpermitted_days_off": unpermitted
    }

def ym_nav(y: int, m: int):
    """Trả về (prev_mm_yyyy, next_mm_yyyy)."""
    prev_y, prev_m = (y-1, 12) if m == 1 else (y, m-1)
    next_y, next_m = (y+1, 1)  if m == 12 else (y, m+1)
    return f"{prev_m:02d}-{prev_y:04d}", f"{next_m:02d}-{next_y:04d}"