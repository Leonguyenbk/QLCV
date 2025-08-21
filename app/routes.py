from flask import Blueprint, render_template, request, current_app
from app.models import Employee, Department
from app import db, utils
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