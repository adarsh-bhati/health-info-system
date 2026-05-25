from flask import Flask
from flask_login import LoginManager
from flask_pymongo import PyMongo
import os

mongo = PyMongo()
login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app():
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

    app = Flask(
        __name__,
        template_folder=os.path.join(basedir, 'templates'),
        static_folder=os.path.join(basedir, 'static')
    )

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "devsecret")

    app.config["MONGO_URI"] = os.getenv("MONGO_URI")

    mongo.init_app(app)
    login_manager.init_app(app)

    from .auth import auth_bp
    from .routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    return app