from flask import Blueprint, render_template, request, current_app, abort, flash, redirect, url_for
from flask_login import login_user, logout_user, current_user, login_required
from app.models import Employee, Department, Absence
from . import db, utils, login
from .forms import ProfileUpdateForm
from .utils import save_picture
from datetime import date
from calendar import monthrange
import os

main = Blueprint('main', __name__)
# Trong file routes của blueprint 'main'
@login.user_loader
def user_load(user_id):
    return utils.get_user_by_id(user_id=user_id)

@main.route('/login', methods=['GET', 'POST'])
def login():
    err_msg = ''
    if request.method.__eq__('POST'):
        username = request.form.get('username')
        password = request.form.get('password')

        user = utils.check_login(username=username,
                                password=password)
        if user:
            login_user(user=user)
            next = request.args.get('next', '/')
            return redirect(next)
        else:
            err_msg = 'Username hoặc mật khẩu không chính xác'

    return render_template('login.html', err_msg=err_msg)

@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Bạn đã đăng xuất.', 'info')
    return redirect(url_for('main.login'))


@main.route('/')
@login_required
def index():
    return render_template('index.html')

@main.route('/employees')
@login_required
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
@login_required
def employee_detail(employee_id):
    employee = utils.get_employee_by_id(employee_id)
    if not employee:
        abort(404)

    avatar_url = url_for(
        'static',
        filename=employee.avatar_url if employee and employee.avatar_url else 'images/default_avatar.png'
    )

    return render_template(
        'employees_details.html',
        employee=employee,
        avatar_url=avatar_url
    )

@main.route('/summary/all', methods=['GET'])
@login_required
def kpi_absence_summary_all():
    # Lấy các tham số từ URL
    page = request.args.get('page', 1, type=int)
    month_str_param = request.args.get('month')  # 'MM-YYYY'
    kw = request.args.get('keyword', type=str)
    department_id = request.args.get('department_id', type=int)

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
@login_required
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

# --- Route cho trang hồ sơ cá nhân ---
@main.route("/profile", methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileUpdateForm()
    employee = current_user.employee
    if form.validate_on_submit():
        # Kiểm tra nếu người dùng upload ảnh mới
        if form.picture.data:
            # Nếu có ảnh cũ và KHÔNG phải ảnh mặc định thì xóa
            if employee.avatar_url and employee.avatar_url != "images/default_avatar.png":
                old_path = os.path.join(current_app.root_path, 'static', employee.avatar_url)
                try:
                    if os.path.exists(old_path):
                        os.remove(old_path)
                except Exception as e:
                    print(f"Lỗi xóa ảnh cũ: {e}")

            # Lưu ảnh mới
            picture_file = save_picture(form.picture.data)
            employee.avatar_url = picture_file

        # Cập nhật thông tin nhân viên
        employee.name = form.name.data
        employee.email = form.email.data
        employee.phone = form.phone.data
        db.session.commit()
        flash('Thông tin cá nhân của bạn đã được cập nhật!', 'success')
        return redirect(url_for('main.profile'))
    elif request.method == 'GET':
        # Điền thông tin hiện tại vào form
        if employee:
            form.name.data = employee.name
            form.email.data = employee.email
            form.phone.data = employee.phone

    # Lấy đường dẫn ảnh để hiển thị
    image_file = url_for('static', filename=employee.avatar_url or 'images/default_avatar.png')
    print(employee.avatar_url)
    print(image_file)
    return render_template('profile.html', title='Hồ sơ cá nhân', form=form, image_file=image_file)