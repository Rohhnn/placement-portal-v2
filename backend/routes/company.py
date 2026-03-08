from flask import Blueprint, request, jsonify
from datetime import datetime
from backend.extensions import db
from backend.models import PlacementDrive, Application
from backend.routes.auth import token_required, role_required

company_bp = Blueprint('company', __name__)


@company_bp.route('/api/company/dashboard')
@token_required
@role_required('company')
def dashboard(current_user):
    company = current_user.company
    drives = PlacementDrive.query.filter_by(company_id=company.id).all()
    return jsonify({
        'company': {
            'id': company.id,
            'company_name': company.company_name,
            'industry': company.industry,
            'website': company.website,
            'hr_contact': company.hr_contact,
            'description': company.description
        },
        'drives': [{
            'id': d.id,
            'job_title': d.job_title,
            'salary_range': d.salary_range,
            'application_deadline': str(d.application_deadline) if d.application_deadline else None,
            'status': d.status,
            'application_count': len(d.applications)
        } for d in drives]
    })


@company_bp.route('/api/company/drives', methods=['POST'])
@token_required
@role_required('company')
def create_drive(current_user):
    if current_user.company.approval_status != 'approved':
        return jsonify({'error': 'Company must be approved to create drives'}), 403

    data = request.get_json()
    deadline = None
    if data.get('application_deadline'):
        deadline = datetime.strptime(data['application_deadline'], '%Y-%m-%d').date()

    drive = PlacementDrive(
        company_id=current_user.company.id,
        job_title=data.get('job_title'),
        job_description=data.get('job_description'),
        eligibility_criteria=data.get('eligibility_criteria'),
        skills_required=data.get('skills_required'),
        salary_range=data.get('salary_range'),
        application_deadline=deadline,
        status='pending'
    )
    db.session.add(drive)
    db.session.commit()
    return jsonify({'message': 'Drive created, awaiting admin approval'}), 201


@company_bp.route('/api/company/drive/<int:did>/close', methods=['PUT'])
@token_required
@role_required('company')
def close_drive(current_user, did):
    drive = PlacementDrive.query.get_or_404(did)
    if drive.company_id != current_user.company.id:
        return jsonify({'error': 'Access denied'}), 403
    drive.status = 'closed'
    db.session.commit()
    return jsonify({'message': 'Drive closed'})


@company_bp.route('/api/company/drive/<int:did>/reopen', methods=['PUT'])
@token_required
@role_required('company')
def reopen_drive(current_user, did):
    drive = PlacementDrive.query.get_or_404(did)
    if drive.company_id != current_user.company.id:
        return jsonify({'error': 'Access denied'}), 403
    drive.status = 'approved'
    db.session.commit()
    return jsonify({'message': 'Drive reopened'})


@company_bp.route('/api/company/drive/<int:did>/applications')
@token_required
@role_required('company')
def get_applications(current_user, did):
    drive = PlacementDrive.query.get_or_404(did)
    if drive.company_id != current_user.company.id:
        return jsonify({'error': 'Access denied'}), 403

    applications = Application.query.filter_by(drive_id=did).all()
    return jsonify([{
        'id': a.id,
        'student': {
            'id': a.student.id,
            'full_name': a.student.full_name,
            'email': a.student.email,
            'education': a.student.education,
            'skills': a.student.skills,
            'resume_path': a.student.resume_path
        },
        'application_date': a.application_date.strftime('%Y-%m-%d'),
        'status': a.status
    } for a in applications])


@company_bp.route('/api/company/application/<int:aid>/update', methods=['PUT'])
@token_required
@role_required('company')
def update_application(current_user, aid):
    application = Application.query.get_or_404(aid)
    if application.drive.company_id != current_user.company.id:
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    new_status = data.get('status')
    if new_status in ['shortlisted', 'selected', 'rejected']:
        application.status = new_status
        db.session.commit()
        return jsonify({'message': f'Status updated to {new_status}'})
    return jsonify({'error': 'Invalid status'}), 400