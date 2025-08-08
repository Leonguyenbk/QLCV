import pandas as pd
from datetime import datetime
from app import app, db
from app.models import Employee


def parse_date(value):
    if pd.isnull(value):
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.strptime(str(value), '%Y-%m-%d')
    except:
        return None

with app.app_context():
    df = pd.read_excel('DSDLTT.xlsx')

    for _, row in df.iterrows():
        emp = Employee(
            name=row['name'],
            year_of_birth=parse_date(row['year_of_birth']),
            position=row['position'],
            email=None if pd.isnull(row['email']) else row['email'],
            phone=None if pd.isnull(row['phone']) else row['phone'],
            department_id=int(row['department_id']) if not pd.isnull(row['department_id']) else None
        )
        db.session.add(emp)  # <-- QUAN TRỌNG!

    db.session.commit()
    print("Đã import thành công dữ liệu nhân viên.")
