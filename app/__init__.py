from flask import Flask
from flask_sqlalchemy import SQLAlchemy

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:12345678@localhost/dbdltt?charset=utf8mb4'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
    app.config['PAGE_SIZE'] = 10
    app.secret_key = 'mysecretkey'

    db.init_app(app)

    # Đăng ký route
    from app.routes import main
    app.register_blueprint(main)

    return app

db = SQLAlchemy()