import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, send_from_directory
from backend.config import Config
from backend.extensions import db, cache
from werkzeug.security import generate_password_hash


def create_app():
    app = Flask(__name__, static_folder='../static')
    app.config.from_object(Config)

    db.init_app(app)
    cache.init_app(app)

    from backend.routes.auth import auth_bp
    from backend.routes.admin import admin_bp
    from backend.routes.company import company_bp
    from backend.routes.student import student_bp
    from backend.routes.jobs import jobs_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(jobs_bp)

    with app.app_context():
        from backend.models import User
        db.create_all()
        seed_admin()

    return app


def seed_admin():
    from backend.models import User
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        admin = User(
            username='admin',
            password=generate_password_hash('admin123'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()


app = create_app()


@app.route('/')
def serve_frontend():
    return send_from_directory('../frontend', 'index.html')


if __name__ == '__main__':
    app.run(debug=True, port=5001)