from flask import Blueprint, jsonify
from backend.routes.auth import token_required, role_required

jobs_bp = Blueprint('jobs', __name__)


@jobs_bp.route('/api/student/export-csv', methods=['POST'])
@token_required
@role_required('student')
def trigger_csv_export(current_user):
    from backend.celery_worker import export_applications_csv
    task = export_applications_csv.delay(current_user.student.id)
    return jsonify({'message': 'Export started', 'task_id': task.id}), 202


@jobs_bp.route('/api/jobs/task-status/<task_id>')
@token_required
def check_task_status(current_user, task_id):
    from backend.celery_worker import celery_app
    task = celery_app.AsyncResult(task_id)
    if task.state == 'SUCCESS':
        return jsonify({'status': 'completed', 'result': task.result})
    elif task.state == 'FAILURE':
        return jsonify({'status': 'failed'}), 500
    return jsonify({'status': 'pending'})


@jobs_bp.route('/api/admin/trigger-report', methods=['POST'])
@token_required
@role_required('admin')
def trigger_monthly_report(current_user):
    from backend.celery_worker import generate_monthly_report
    task = generate_monthly_report.delay()
    return jsonify({'message': 'Report generation started', 'task_id': task.id}), 202


@jobs_bp.route('/api/admin/trigger-reminders', methods=['POST'])
@token_required
@role_required('admin')
def trigger_reminders(current_user):
    from backend.celery_worker import send_daily_reminders
    task = send_daily_reminders.delay()
    return jsonify({'message': 'Reminders job started', 'task_id': task.id}), 202