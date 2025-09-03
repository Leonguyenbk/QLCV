from flask_babel import Babel 
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
babel = Babel()  # tạo instance extension

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:12345678@localhost/dbdltt?charset=utf8mb4'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['BABEL_DEFAULT_LOCALE'] = 'vi'
    app.config['BABEL_DEFAULT_TIMEZONE'] = 'Asia/Ho_Chi_Minh'
    app.config['PAGE_SIZE'] = 20
    app.secret_key = 'mysecretkey'

    db.init_app(app)
    migrate.init_app(app, db)
    babel.init_app(app, locale_selector=lambda: request.accept_languages.best_match(['vi', 'en']) or 'vi',
                    timezone_selector=lambda: 'Asia/Ho_Chi_Minh')
    login.init_app(app)
    from . import models
    from .admin import init_admin   # <<< quan trọng
    with app.app_context():
        init_admin(app)       

    # Đăng ký route
    from app.routes import main
    app.register_blueprint(main)

    return app


login.login_view = 'main.login' # Tên blueprint.tên_hàm_route
login.login_message = 'Vui lòng đăng nhập để truy cập trang này.'
login.login_message_category = 'warning'