from flask import Flask
from flask_login import LoginManager
from flask_pymongo import PyMongo
import os

mongo = PyMongo()
login_manager = LoginManager()
login_manager.login_view = "auth.login"

knowledge_loaded = False


def create_app():
    global knowledge_loaded

    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

    app = Flask(
        __name__,
        template_folder=os.path.join(basedir, 'templates'),
        static_folder=os.path.join(basedir, 'static')
    )

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "devsecret")

    from config import MONGO_URI
    app.config["MONGO_URI"] = MONGO_URI

    mongo.init_app(app)
    login_manager.init_app(app)

    # Load medical knowledge base only once
    if not knowledge_loaded:
        from pdf_loader import load_pdf
        from rag import chunk_text, build_index

        print("Loading medical knowledge base...")

        pdf_path = os.path.join(basedir, "common_disease_symptoms.pdf")

        if os.path.exists(pdf_path):
            text = load_pdf(pdf_path)

            chunks = chunk_text(text)

            build_index(
                chunks,
                "Common Disease Knowledge Base",
                user_id=None
            )

            print("Medical knowledge loaded.")

        else:
            print("Knowledge PDF not found.")

        knowledge_loaded = True

    from .auth import auth_bp
    from .routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    return app