from flask import Blueprint, request, jsonify
from backend.extensions import db, cache
from backend.models import Company, Student, PlacementDrive, Application
from backend.routes.auth import token_required, role_required

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/api/admin/dashboard')
@token_required
@role_required('admin')
@cache.cached(timeout=60, key_prefix='admin_dashboard')
def dashboard(current_user):
    return jsonify({
        'total_companies': Company.query.count(),
        'total_students': Student.query.count(),
        'total_drives': PlacementDrive.query.count(),
        'total_applications': Application.query.count(),
        'pending_companies': Company.query.filter_by(approval_status='pending').count(),
        'pending_drives': PlacementDrive.query.filter_by(status='pending').count()
    })


@admin_bp.route('/api/admin/companies')
@token_required
@role_required('admin')
def get_companies(current_user):
    search = request.args.get('search', '')
    if search:
        companies = Company.query.filter(
            (Company.company_name.ilike(f'%{search}%')) |
            (Company.industry.ilike(f'%{search}%'))
        ).all()
    else:
        companies = Company.query.all()

    return jsonify([{
        'id': c.id,
        'company_name': c.company_name,
        'industry': c.industry,
        'website': c.website,
        'hr_contact': c.hr_contact,
        'description': c.description,
        'approval_status': c.approval_status,
        'is_blacklisted': c.is_blacklisted
    } for c in companies])


@admin_bp.route('/api/admin/company/<int:cid>/approve', methods=['PUT'])
@token_required
@role_required('admin')
def approve_company(current_user, cid):
    company = Company.query.get_or_404(cid)
    company.approval_status = 'approved'
    db.session.commit()
    return jsonify({'message': f'{company.company_name} approved'})


@admin_bp.route('/api/admin/company/<int:cid>/reject', methods=['PUT'])
@token_required
@role_required('admin')
def reject_company(current_user, cid):
    company = Company.query.get_or_404(cid)
    company.approval_status = 'rejected'
    db.session.commit()
    return jsonify({'message': f'{company.company_name} rejected'})


@admin_bp.route('/api/admin/company/<int:cid>/blacklist', methods=['PUT'])
@token_required
@role_required('admin')
def blacklist_company(current_user, cid):
    company = Company.query.get_or_404(cid)
    company.is_blacklisted = not company.is_blacklisted
    db.session.commit()
    status = 'blacklisted' if company.is_blacklisted else 'unblacklisted'
    return jsonify({'message': f'{company.company_name} {status}'})


@admin_bp.route('/api/admin/students')
@token_required
@role_required('admin')
def get_students(current_user):
    search = request.args.get('search', '')
    if search:
        students = Student.query.filter(
            (Student.full_name.ilike(f'%{search}%')) |
            (Student.email.ilike(f'%{search}%')) |
            (Student.phone.ilike(f'%{search}%'))
        ).all()
    else:
        students = Student.query.all()

    return jsonify([{
        'id': s.id,
        'full_name': s.full_name,
        'email': s.email,
        'phone': s.phone,
        'education': s.education,
        'skills': s.skills,
        'is_blacklisted': s.is_blacklisted
    } for s in students])


@admin_bp.route('/api/admin/student/<int:sid>/blacklist', methods=['PUT'])
@token_required
@role_required('admin')
def blacklist_student(current_user, sid):
    student = Student.query.get_or_404(sid)
    student.is_blacklisted = not student.is_blacklisted
    db.session.commit()
    status = 'blacklisted' if student.is_blacklisted else 'unblacklisted'
    return jsonify({'message': f'{student.full_name} {status}'})


@admin_bp.route('/api/admin/drives')
@token_required
@role_required('admin')
def get_drives(current_user):
    drives = PlacementDrive.query.all()
    return jsonify([{
        'id': d.id,
        'job_title': d.job_title,
        'company_name': d.company.company_name,
        'salary_range': d.salary_range,
        'application_deadline': str(d.application_deadline) if d.application_deadline else None,
        'status': d.status,
        'application_count': len(d.applications)
    } for d in drives])


@admin_bp.route('/api/admin/drive/<int:did>/approve', methods=['PUT'])
@token_required
@role_required('admin')
def approve_drive(current_user, did):
    drive = PlacementDrive.query.get_or_404(did)
    drive.status = 'approved'
    db.session.commit()
    return jsonify({'message': f'Drive "{drive.job_title}" approved'})


@admin_bp.route('/api/admin/drive/<int:did>/reject', methods=['PUT'])
@token_required
@role_required('admin')
def reject_drive(current_user, did):
    drive = PlacementDrive.query.get_or_404(did)
    drive.status = 'rejected'
    db.session.commit()
    return jsonify({'message': f'Drive "{drive.job_title}" rejected'})


@admin_bp.route('/api/admin/applications')
@token_required
@role_required('admin')
def get_applications(current_user):
    applications = Application.query.all()
    return jsonify([{
        'id': a.id,
        'student_name': a.student.full_name,
        'drive_title': a.drive.job_title,
        'company_name': a.drive.company.company_name,
        'application_date': a.application_date.strftime('%Y-%m-%d'),
        'status': a.status
    } for a in applications])