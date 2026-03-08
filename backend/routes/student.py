import os
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from backend.extensions import db
from backend.models import PlacementDrive, Application, Student
from backend.routes.auth import token_required, role_required

student_bp = Blueprint('student', __name__)


@student_bp.route('/api/student/dashboard')
@token_required
@role_required('student')
def dashboard(current_user):
    student = current_user.student
    applications = Application.query.filter_by(student_id=student.id).all()
    approved_drives_count = PlacementDrive.query.filter_by(status='approved').count()

    notifications = [{
        'drive_title': a.drive.job_title,
        'company_name': a.drive.company.company_name,
        'status': a.status
    } for a in applications if a.status in ['shortlisted', 'selected', 'rejected']]

    return jsonify({
        'student': {
            'full_name': student.full_name,
            'email': student.email
        },
        'available_drives': approved_drives_count,
        'total_applications': len(applications),
        'notifications': notifications
    })


@student_bp.route('/api/student/drives')
@token_required
@role_required('student')
def browse_drives(current_user):
    search = request.args.get('search', '')
    if search:
        drives = PlacementDrive.query.filter(
            PlacementDrive.status == 'approved',
            (PlacementDrive.job_title.ilike(f'%{search}%')) |
            (PlacementDrive.skills_required.ilike(f'%{search}%'))
        ).all()
    else:
        drives = PlacementDrive.query.filter_by(status='approved').all()

    applied_ids = [a.drive_id for a in Application.query.filter_by(student_id=current_user.student.id).all()]

    return jsonify([{
        'id': d.id,
        'job_title': d.job_title,
        'company_name': d.company.company_name,
        'skills_required': d.skills_required,
        'salary_range': d.salary_range,
        'application_deadline': str(d.application_deadline) if d.application_deadline else None,
        'already_applied': d.id in applied_ids
    } for d in drives])


@student_bp.route('/api/student/apply/<int:did>', methods=['POST'])
@token_required
@role_required('student')
def apply_drive(current_user, did):
    drive = PlacementDrive.query.get_or_404(did)
    if drive.status != 'approved':
        return jsonify({'error': 'Drive is not accepting applications'}), 400

    existing = Application.query.filter_by(
        student_id=current_user.student.id,
        drive_id=did
    ).first()
    if existing:
        return jsonify({'error': 'Already applied to this drive'}), 400

    application = Application(
        student_id=current_user.student.id,
        drive_id=did,
        status='applied'
    )
    db.session.add(application)
    db.session.commit()
    return jsonify({'message': f'Applied to "{drive.job_title}"'}), 201


@student_bp.route('/api/student/applications')
@token_required
@role_required('student')
def my_applications(current_user):
    applications = Application.query.filter_by(student_id=current_user.student.id).all()
    return jsonify([{
        'id': a.id,
        'drive_title': a.drive.job_title,
        'company_name': a.drive.company.company_name,
        'application_date': a.application_date.strftime('%Y-%m-%d'),
        'status': a.status
    } for a in applications])


@student_bp.route('/api/student/profile', methods=['GET', 'PUT'])
@token_required
@role_required('student')
def profile(current_user):
    student = current_user.student

    if request.method == 'GET':
        return jsonify({
            'full_name': student.full_name,
            'email': student.email,
            'phone': student.phone,
            'education': student.education,
            'skills': student.skills,
            'resume_path': student.resume_path
        })

    # PUT: update profile
    content_type = request.content_type or ''
    if 'multipart/form-data' in content_type:
        form = request.form
    else:
        form = request.get_json()

    student.full_name = form.get('full_name', student.full_name)
    student.email = form.get('email', student.email)
    student.phone = form.get('phone', student.phone)
    student.education = form.get('education', student.education)
    student.skills = form.get('skills', student.skills)

    if 'resume' in request.files:
        file = request.files['resume']
        if file.filename:
            upload_dir = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_dir, exist_ok=True)
            filename = secure_filename(f"{current_user.username}_{file.filename}")
            file.save(os.path.join(upload_dir, filename))
            student.resume_path = filename

    db.session.commit()
    return jsonify({'message': 'Profile updated'})


@student_bp.route('/api/student/<int:sid>/view')
@token_required
def view_student(current_user, sid):
    if current_user.role not in ['admin', 'company']:
        return jsonify({'error': 'Access denied'}), 403

    student = Student.query.get_or_404(sid)
    applications = Application.query.filter_by(student_id=sid).all()

    return jsonify({
        'student': {
            'full_name': student.full_name,
            'email': student.email,
            'phone': student.phone,
            'education': student.education,
            'skills': student.skills,
            'resume_path': student.resume_path
        },
        'applications': [{
            'drive_title': a.drive.job_title,
            'company_name': a.drive.company.company_name,
            'application_date': a.application_date.strftime('%Y-%m-%d'),
            'status': a.status
        } for a in applications]
    })