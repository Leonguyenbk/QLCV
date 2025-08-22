from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:12345678@localhost/dbdltt?charset=utf8mb4'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PAGE_SIZE'] = 20
    app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'  # theme cho admin
    app.config['BABEL_DEFAULT_LOCALE'] = 'vi'  # set locale là tiếng Việt
    app.secret_key = 'mysecretkey'

    db.init_app(app)
    migrate.init_app(app, db)
    from . import models
    from .admin import init_admin   # <<< quan trọng
    with app.app_context():
        init_admin(app)       

    # Đăng ký route
    from app.routes import main
    app.register_blueprint(main)

    return app

db = SQLAlchemy()
migrate = Migrate()