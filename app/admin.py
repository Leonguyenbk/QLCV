# Tạo trang admin để quản lý nhân viên, tổ chuyên môn và chi tiết công việc
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from app import create_app, db
from app.models import Employee, Department, JobDetail

admin = Admin(app, name='Admin Panel', template_mode='bootstrap4')

class EmployeeModelView(ModelView):
    column_list = ['name', 'year_of_birth', 'position', 'email', 'phone', 'department']
    column_searchable_list = ['name', 'position']
    column_filters = ['department.name']
    form_columns = ['name', 'year_of_birth', 'position', 'email', 'phone', 'department']

admin.add_view(EmployeeModelView(Employee, db.session))
admin.add_view(ModelView(Department, db.session))