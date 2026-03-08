import jwt
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from backend.extensions import db
from backend.models import User, Company, Student

auth_bp = Blueprint('auth', __name__)


def generate_token(user):
    payload = {
        'user_id': user.id,
        'role': user.role,
        'exp': datetime.utcnow() + timedelta(hours=current_app.config['JWT_EXPIRATION_HOURS'])
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')


def token_required(f):
    """Decorator to protect routes with JWT authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
            if not current_user or not current_user.is_active_user:
                return jsonify({'error': 'Invalid or deactivated user'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(current_user, *args, **kwargs)
    return decorated


def role_required(role):
    """Decorator to restrict access to a specific role."""
    def decorator(f):
        @wraps(f)
        def decorated(current_user, *args, **kwargs):
            if current_user.role != role:
                return jsonify({'error': 'Access denied'}), 403
            return f(current_user, *args, **kwargs)
        return decorated
    return decorator


@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({'error': 'Invalid username or password'}), 401

    if not user.is_active_user:
        return jsonify({'error': 'Account has been deactivated'}), 403

    if user.role == 'company' and user.company:
        if user.company.approval_status != 'approved':
            return jsonify({'error': 'Company registration is pending approval'}), 403
        if user.company.is_blacklisted:
            return jsonify({'error': 'Company has been blacklisted'}), 403

    if user.role == 'student' and user.student:
        if user.student.is_blacklisted:
            return jsonify({'error': 'Account has been blacklisted'}), 403

    token = generate_token(user)
    return jsonify({
        'token': token,
        'user': {
            'id': user.id,
            'username': user.username,
            'role': user.role
        }
    })


@auth_bp.route('/api/register', methods=['POST'])
def register():
    content_type = request.content_type or ''

    # Handle both JSON and form-data (form-data needed for file upload)
    if 'multipart/form-data' in content_type:
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
    else:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        role = data.get('role')

    if role not in ['company', 'student']:
        return jsonify({'error': 'Invalid role'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400

    user = User(
        username=username,
        password=generate_password_hash(password),
        role=role
    )
    db.session.add(user)
    db.session.flush()

    if role == 'company':
        if 'multipart/form-data' in content_type:
            form = request.form
        else:
            form = data
        company = Company(
            user_id=user.id,
            company_name=form.get('company_name'),
            industry=form.get('industry'),
            website=form.get('website'),
            hr_contact=form.get('hr_contact'),
            description=form.get('description'),
            approval_status='pending'
        )
        db.session.add(company)

    elif role == 'student':
        if 'multipart/form-data' in content_type:
            form = request.form
        else:
            form = data

        resume_path = None
        if 'resume' in request.files:
            file = request.files['resume']
            if file.filename:
                upload_dir = current_app.config['UPLOAD_FOLDER']
                os.makedirs(upload_dir, exist_ok=True)
                filename = secure_filename(f"{username}_{file.filename}")
                file.save(os.path.join(upload_dir, filename))
                resume_path = filename

        student = Student(
            user_id=user.id,
            full_name=form.get('full_name'),
            email=form.get('email'),
            phone=form.get('phone'),
            education=form.get('education'),
            skills=form.get('skills'),
            resume_path=resume_path
        )
        db.session.add(student)

    db.session.commit()

    msg = 'Registration successful. Awaiting admin approval.' if role == 'company' else 'Registration successful.'
    return jsonify({'message': msg}), 201