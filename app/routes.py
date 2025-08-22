from flask import Blueprint, render_template, request, current_app, abort
from app.models import Employee, Department, Absence
from app import db, utils
from datetime import date
from calendar import monthrange
import math


main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/employees')
def list_employees():
    page = request.args.get('page', 1, type=int)
    kw = request.args.get('keyword', type=str)
    department_id = request.args.get('category_id', type=int)

    q = Employee.query
    if kw:
        q = q.filter(Employee.name.ilike(f"%{kw.strip()}%"))
    if department_id:
        q = q.filter(Employee.department_id == department_id)

    q = q.order_by(Employee.id.asc())

    per_page = current_app.config.get('PAGE_SIZE', 10)
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        'employees.html',
        employees=pagination.items,
        pagination=pagination,
        departments=Department.query.all(),
        selected_department=department_id
    )

@main.route("/employees/<int:employee_id>")
def employee_detail(employee_id):
    employee = utils.get_employee_by_id(employee_id)
    return render_template('employees_details.html', employee=employee)

@main.route('/summary/all', methods=['GET'])
def kpi_absence_summary_all():
    # Lấy các tham số từ URL
    page = request.args.get('page', 1, type=int)
    month_str_param = request.args.get('month')  # 'MM-YYYY'
    kw = request.args.get('keyword', type=str)
    department_id = request.args.get('department_id', type=int)
    export = request.args.get('export')  # 'csv' nếu muốn tải CSV

    # Xử lý tháng/năm và điều hướng
    y, m = utils.parse_month(month_str_param)
    prev_month_mm, next_month_mm = utils.ym_nav(y, m)
    month_str_mm = f"{m:02d}-{y}"

    # Xây dựng câu truy vấn nhân viên với bộ lọc
    q = db.session.query(Employee)
    if kw:
        q = q.filter(Employee.name.ilike(f"%{kw.strip()}%"))
    if department_id:
        q = q.filter(Employee.department_id == department_id)

    pagination = q.order_by(Employee.name.asc()).paginate(
        page=page, per_page=20, error_out=False
    )
    employees = pagination.items

    # Tính toán KPI cho các nhân viên đã lọc
    rows = []
    for e in employees:
        s = utils.absence_summary(db.session, e.id, y, m)
        score = 100 - 2 * s["permitted_days_off"] - 10 * s["unpermitted_days_off"]
        score = max(0, min(100, round(score, 2)))
        rows.append({
            "employee": e,
            "total": s["total_days_off"],
            "permitted": s["permitted_days_off"],
            "unpermitted": s["unpermitted_days_off"],
            "kpi_score": score
        })

    # Lấy danh sách phòng ban để hiển thị trong bộ lọc
    departments = db.session.query(Department).order_by(Department.name).all()

    return render_template(
        'kpi/summary_all.html',
        rows=rows,
        year=y, month=m,
        prev_month_mm=prev_month_mm,
        next_month_mm=next_month_mm,
        month_str=month_str_mm,
        pagination=pagination,
        departments=departments,
        keyword=kw,
        selected_department=department_id
    )

@main.route("/kpi_detail/<int:employee_id>", methods=["GET"])
def kpi_detail(employee_id: int):
    month_str_param = request.args.get("month")   # giờ nhận 'mm-yyyy'

    employee = db.session.get(Employee, employee_id) or abort(404)

    y, m = utils.parse_month(month_str_param)
    month_str_mm = f"{m:02d}-{y:04d}"                 # để hiển thị/giữ nguyên mm-yyyy
    prev_month_mm, next_month_mm = utils.ym_nav(y, m)

    start_day = date(y, m, 1)
    end_day = date(y, m, monthrange(y, m)[1])

    s = utils.absence_summary(db.session, employee_id, y, m)
    records = (db.session.query(Absence)
               .filter(Absence.employee_id == employee_id,
                       Absence.work_date >= start_day,
                       Absence.work_date <= end_day)
               .order_by(Absence.work_date.asc())
               .all())

    score = 100 - 2 * s["permitted_days_off"] - 10 * s["unpermitted_days_off"]
    score = max(0, min(100, round(score, 2)))

    return render_template(
        "kpi/detail.html",
        employee=employee,
        year=y, month=m,
        month_str_mm=month_str_mm,
        prev_month_mm=prev_month_mm,
        next_month_mm=next_month_mm,
        summary=s, score=score, records=records
    )
