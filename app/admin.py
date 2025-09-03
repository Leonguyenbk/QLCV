# app/admin.py
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.filters import DateBetweenFilter, FilterEqual
from flask_admin.actions import action
from flask_login import current_user
from flask import abort, flash
from flask_babel import gettext
from wtforms import TextAreaField, ValidationError
from wtforms.fields import PasswordField
from werkzeug.security import generate_password_hash
from sqlalchemy.orm.attributes import get_history
from . import db
from datetime import date
from .models import Employee, Department, JobDetail, Absence, OrgRole, User, SystemRole, EmployeeHistory  
from markupsafe import Markup

admin = Admin(name='Admin Panel', template_mode='bootstrap4', url='/admin')

# === mapping VN ===
VI_ROLE_CHOICES = [
    ('MEMBER',    'Nhân viên'),
    ('TEAM_LEAD', 'Tổ trưởng'),
    ('DEPT_HEAD', 'Trưởng/ phó phòng'),
]
VI_ROLE_LABEL = dict(VI_ROLE_CHOICES)
ROLE_BADGE = {
    'MEMBER':    'secondary',
    'TEAM_LEAD': 'info',
    'DEPT_HEAD': 'primary',
}

def _role_value(val):
    # nhận Enum hoặc string -> trả "MEMBER" | "TEAM_LEAD" | ...
    return getattr(val, 'value', val)

def _role_label(val) -> str:
    return VI_ROLE_LABEL.get(_role_value(val), '')

# fields cần tracking (phù hợp với model Employee hiện tại)
TRACKED_FIELDS = {"department_id", "position", "org_role"}

def _enum_val(x):
    return x.value if hasattr(x, "value") else x

def infer_change_type(changed: set[str]) -> str:
    # Ưu tiên theo nghiệp vụ
    if "department_id" in changed:
        return "Chuyển bộ phận"
    if "position" in changed:
        return "Chức vụ"
    if "org_role" in changed:
        return "Vai trò"
    return "Cập nhật"

class UserModelView(ModelView):
    # Chỉ cho phép ADMIN
    def is_accessible(self):
        return current_user.is_authenticated and current_user.role.value == "ADMIN"
    def inaccessible_callback(self, name, **kwargs):
        abort(403)

    column_list = ['username', 'employee', 'role']
    column_labels = {
        'username': 'Tên đăng nhập',
        'employee': 'Nhân viên',
        'role': 'Quyền hệ thống'
    }
    form_columns = ['username', 'password', 'employee', 'role']
    column_searchable_list = ['username']
    column_filters = ['role', 'employee']

    # Thêm trường password ảo trong form
    form_extra_fields = {
        'password': PasswordField('Mật khẩu')
    }

    def on_model_change(self, form, model, is_created):
        """Hash mật khẩu trước khi lưu"""
        if form.password.data:
            model.password_hash = generate_password_hash(form.password.data)
        super().on_model_change(form, model, is_created)

class EmployeeModelView(ModelView):
    column_list = ['name', 'department', 'position', 'email', 'phone', 'org_role']
    column_labels = {
        'name': 'Họ tên', 'department': 'Tổ/Phòng', 'position': 'Vị trí',
        'email': 'Email', 'phone': 'Điện thoại', 'org_role': 'Vai trò'
    }
    column_searchable_list = ['name', 'position', 'email', 'phone']
    form_columns = ['name', 'year_of_birth', 'position', 'email', 'phone', 'department', 'org_role', 'reason']
        # Hiển thị tiếng Việt ở bảng (list view)
    column_formatters = {
        'org_role': lambda v, c, m, p: (m.org_role.value if m.org_role else ''),
        'department': lambda v, c, m, p: (m.department.name if m.department else '')
    }
    column_filters = [
        'department',
        FilterEqual(Employee.org_role, 'Vai trò',
                    options=[(e.value, e.value) for e in OrgRole])
    ]
    form_choices = {
        'org_role': [
            ('MEMBER', 'Nhân viên'),
            ('TEAM_LEAD', 'Tổ trưởng'), 
            ('DEPT_HEAD', 'Trưởng/phó phòng')
        ]
    }
    form_extra_fields = { 'reason': TextAreaField('Lý do điều chỉnh') }
        # Giới hạn quyền truy cập
    def is_accessible(self):
        # Cho phép ADMIN, HR_GENERAL và HR_DEPARTMENT
        print(current_user.role)
        allowed_roles = ["ADMIN", "HR_GENERAL", "HR_DEPARTMENT"]
        return current_user.is_authenticated and current_user.role.value in allowed_roles

    # Nếu không có quyền thì trả về 403 Forbidden
    def inaccessible_callback(self, name, **kwargs):
        abort(403)

    def _same_department(self, obj) -> bool:
        return (obj is not None and
                current_user.is_authenticated and
                getattr(current_user, "employee", None) is not None and
                obj.department_id == current_user.employee.department_id)

    def get_one(self, id):
        obj = super().get_one(id)
        # HR_DEPARTMENT chỉ được xem/sửa người cùng phòng
        if current_user.is_authenticated and current_user.role.value == "HR_DEPARTMENT":
            if not self._same_department(obj):
                abort(403)  # hoặc abort(404) nếu muốn “giấu” bản ghi
        return obj
    
    def get_query(self):
        query = super().get_query()
        # Nếu là HR_DEPARTMENT → chỉ xem nhân sự trong phòng của mình
        if current_user.is_authenticated and current_user.role.value == "HR_DEPARTMENT":
            return query.filter(Employee.department_id == current_user.employee.department_id)
        return query
    
    def update_model(self, form, model):
        """
        Ghi đè để chèn db.session.flush() vào giữa,
        giúp on_model_change phát hiện được thay đổi trên foreign key.
        """
        if current_user.role.value == "HR_DEPARTMENT" and not self._same_department(model):
            abort(403)
        try:
            form.populate_obj(model)
            db.session.flush()  # Đồng bộ thay đổi vào session, giúp get_history hoạt động
            self._on_model_change(form, model, False)
            self.session.commit()
        except Exception as ex:
            if not self.handle_view_exception(ex):
                flash(gettext('Failed to update record. %(error)s', error=str(ex)), 'error')
            self.session.rollback()
            return False
        else:
            self.after_model_change(form, model, False)
        return True

    def get_count_query(self):
        query = super().get_count_query()
        # Đồng bộ với get_query()
        if current_user.is_authenticated and current_user.role.value == "HR_DEPARTMENT":
            return query.filter(Employee.department_id == current_user.employee.department_id)
        return query

    def on_model_change(self, form, model, is_created):
        # Chuẩn hoá enum nếu form trả về string
        if isinstance(model.org_role, str):
            model.org_role = OrgRole[model.org_role]

        # ----- CREATE: mở kỳ đầu tiên -----
        if is_created:
            db.session.add(EmployeeHistory(
                employee_id=model.id,
                effective_from=date.today(),
                department_id=model.department_id,
                position=model.position,
                org_role=model.org_role,
                change_type="CREATE",
                reason=(form.reason.data if hasattr(form, "reason") else None),
                source="admin",
                changed_by=getattr(current_user, "username", "system"),
            ))
            return super().on_model_change(form, model, is_created)

        # ===== UPDATE =====
        # 1) LẤY GIÁ TRỊ MỚI TỪ FORM (đặc biệt department là QuerySelectField -> object)
        if hasattr(form, "department") and form.department.data is not None:
            dep_obj_or_id = form.department.data
            new_department_id = getattr(dep_obj_or_id, "id", dep_obj_or_id)  # object -> id
        else:
            new_department_id = model.department_id  # fallback

        new_position = form.position.data if hasattr(form, "position") else model.position

        if hasattr(form, "org_role") and form.org_role.data is not None:
            new_org_role = form.org_role.data
            if isinstance(new_org_role, str):
                new_org_role = OrgRole[new_org_role]
        else:
            new_org_role = model.org_role

        # 2) LẤY SNAPSHOT HIỆN HÀNH (kỳ đang mở) TỪ EmployeeHistory
        current_hist = (EmployeeHistory.query
                        .filter_by(employee_id=model.id, effective_to=None)
                        .order_by(EmployeeHistory.effective_from.desc(), EmployeeHistory.id.desc())
                        .first())

        old_dep  = _enum_val(getattr(current_hist, "department_id", None)) if current_hist else None
        old_pos  = _enum_val(getattr(current_hist, "position", None))      if current_hist else None
        old_role = _enum_val(getattr(current_hist, "org_role", None))      if current_hist else None

        new_dep  = _enum_val(new_department_id)
        new_pos  = _enum_val(new_position)
        new_role = _enum_val(new_org_role)

        changed = set()
        if new_dep  != old_dep:  changed.add("department_id")
        if new_pos  != old_pos:  changed.add("position")
        if new_role != old_role: changed.add("org_role")

        # --- DEBUG nếu cần ---
        # print("OLD:", old_dep, old_pos, old_role)
        # print("NEW:", new_dep, new_pos, new_role)
        # print("CHANGED:", changed)

        if changed:
            if not getattr(form, "reason", None) or not form.reason.data.strip():
                raise ValidationError("Vui lòng nhập Lý do điều chỉnh.")

            # 3) ĐÓNG KỲ CŨ
            if current_hist:
                current_hist.effective_to = date.today()
                db.session.add(current_hist)

            # 4) MỞ KỲ MỚI (snapshot dùng GIÁ TRỊ MỚI LẤY TỪ FORM)
            db.session.add(EmployeeHistory(
                employee_id=model.id,
                effective_from=date.today(),
                department_id=new_department_id,
                position=new_position,
                org_role=new_org_role,
                change_type=infer_change_type(changed),   # sẽ ra TRANSFER_DEPT nếu đổi phòng
                reason=form.reason.data.strip(),
                source="admin",
                changed_by=getattr(current_user, "username", "system"),
            ))

        return super().on_model_change(form, model, is_created)

def init_admin(app):
    admin.init_app(app)
    admin.add_view(EmployeeModelView(Employee, db.session, name='Nhân viên', endpoint="employee"))
    admin.add_view(UserModelView(User, db.session, name='Tài khoản', endpoint="user"))