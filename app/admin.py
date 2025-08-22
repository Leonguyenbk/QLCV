# app/admin.py
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.filters import DateBetweenFilter, FilterEqual
from flask_admin.actions import action
from wtforms.fields import PasswordField
from werkzeug.security import generate_password_hash
from . import db
from .models import Employee, Department, JobDetail, Absence, OrgRole, User, SystemRole  
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

class UserModelView(ModelView):
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
    form_columns = ['name', 'year_of_birth', 'position', 'email', 'phone', 'department', 'org_role']
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

    def on_model_change(self, form, model, is_created):
        # Chuyển đổi string sang enum trước khi lưu
        if isinstance(model.org_role, str):
            model.org_role = OrgRole[model.org_role]
        return super().on_model_change(form, model, is_created)

class JobDetailModelView(ModelView):
    column_list = ['date_posted', 'title', 'employee', 'description']
    column_searchable_list = ['title', 'description', 'employee.name']
    column_filters = (DateBetweenFilter(JobDetail.date_posted, 'Khoảng ngày'), 'employee')
    form_columns = ['employee', 'date_posted', 'title', 'description']
    form_ajax_refs = {'employee': {'fields': ('name', 'email')}}

class AbsenceAdmin(ModelView):
    column_list = ('work_date', 'employee', 'part', 'is_permitted', 'reason')
    column_labels = {
        'work_date': 'Ngày', 'employee': 'Nhân viên', 'part': 'Buổi',
        'is_permitted': 'Có phép', 'reason': 'Lý do',
    }
    column_default_sort = ('work_date', True)
    column_filters = (
        DateBetweenFilter(Absence.work_date, 'Khoảng ngày'),
        FilterEqual(Absence.part, 'Buổi'),
        FilterEqual(Absence.is_permitted, 'Có phép'),
    )
    column_searchable_list = ('employee.name', 'reason')
    form_columns = ('employee', 'work_date', 'part', 'is_permitted', 'reason')
    form_ajax_refs = {'employee': {'fields': ('name', 'email')}}


    def on_model_change(self, form, model, is_created):
        q = Absence.query.filter_by(
            employee_id=model.employee_id, work_date=model.work_date, part=model.part
        )
        if not is_created:
            q = q.filter(Absence.id != model.id)
        if db.session.query(q.exists()).scalar():
            from wtforms.validators import ValidationError
            raise ValidationError("Đã tồn tại bản ghi chuyên cần cùng Nhân viên / Ngày / Buổi.")
        return super().on_model_change(form, model, is_created)

def init_admin(app):
    admin.init_app(app)
    admin.add_view(EmployeeModelView(Employee, db.session, name='Nhân viên'))
    admin.add_view(AbsenceAdmin(Absence, db.session, name='Chuyên cần'))
    admin.add_view(JobDetailModelView(JobDetail, db.session, name='Công việc'))
    admin.add_view(UserModelView(User, db.session, name='Tài khoản'))