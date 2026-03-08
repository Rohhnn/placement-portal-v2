import os
import sys
import csv
from datetime import datetime
from celery import Celery
from celery.schedules import crontab

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

celery_app = Celery(
    'placement_portal',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1'
)

celery_app.conf.beat_schedule = {
    'daily-interview-reminder': {
        'task': 'backend.celery_worker.send_daily_reminders',
        'schedule': crontab(hour=9, minute=0),
    },
    'monthly-placement-report': {
        'task': 'backend.celery_worker.generate_monthly_report',
        'schedule': crontab(day_of_month=1, hour=8, minute=0),
    },
}
celery_app.conf.timezone = 'Asia/Kolkata'


def get_app():
    from backend.app import create_app
    return create_app()


@celery_app.task
def send_daily_reminders():
    """Send reminders to students about upcoming application deadlines."""
    app = get_app()
    with app.app_context():
        from backend.models import PlacementDrive, Student
        from datetime import date, timedelta

        upcoming_drives = PlacementDrive.query.filter(
            PlacementDrive.status == 'approved',
            PlacementDrive.application_deadline <= date.today() + timedelta(days=3),
            PlacementDrive.application_deadline >= date.today()
        ).all()

        students = Student.query.filter_by(is_blacklisted=False).all()

        reminders_sent = 0
        for drive in upcoming_drives:
            for student in students:
                # In production, send email/SMS/webhook here
                print(f"[REMINDER] {student.full_name}: '{drive.job_title}' deadline is {drive.application_deadline}")
                reminders_sent += 1

        return f"Sent {reminders_sent} reminders for {len(upcoming_drives)} upcoming drives"


@celery_app.task
def generate_monthly_report():
    """Generate monthly placement activity report for admin."""
    app = get_app()
    with app.app_context():
        from backend.models import PlacementDrive, Application, Company, Student

        total_drives = PlacementDrive.query.count()
        total_applications = Application.query.count()
        total_selected = Application.query.filter_by(status='selected').count()
        total_companies = Company.query.filter_by(approval_status='approved').count()
        total_students = Student.query.count()

        report_html = f"""
        <html>
        <head><style>
            body {{ font-family: Arial; padding: 20px; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #343a40; color: white; }}
        </style></head>
        <body>
            <h2>Monthly Placement Report</h2>
            <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            <table>
                <tr><th>Metric</th><th>Count</th></tr>
                <tr><td>Active Companies</td><td>{total_companies}</td></tr>
                <tr><td>Total Students</td><td>{total_students}</td></tr>
                <tr><td>Total Placement Drives</td><td>{total_drives}</td></tr>
                <tr><td>Total Applications</td><td>{total_applications}</td></tr>
                <tr><td>Students Selected</td><td>{total_selected}</td></tr>
            </table>
        </body>
        </html>
        """

        # Save report to file
        reports_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        filename = f"monthly_report_{datetime.now().strftime('%Y_%m')}.html"
        filepath = os.path.join(reports_dir, filename)
        with open(filepath, 'w') as f:
            f.write(report_html)

        # In production, send via email to admin
        print(f"[REPORT] Monthly report saved: {filename}")
        return f"Report generated: {filename}"


@celery_app.task
def export_applications_csv(student_id):
    """Export a student's application history as CSV."""
    app = get_app()
    with app.app_context():
        from backend.models import Application, Student

        student = Student.query.get(student_id)
        if not student:
            return "Student not found"

        applications = Application.query.filter_by(student_id=student_id).all()

        exports_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'exports')
        os.makedirs(exports_dir, exist_ok=True)
        filename = f"applications_{student.user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(exports_dir, filename)

        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Student ID', 'Company Name', 'Drive Title', 'Application Status', 'Application Date'])
            for a in applications:
                writer.writerow([
                    student.id,
                    a.drive.company.company_name,
                    a.drive.job_title,
                    a.status,
                    a.application_date.strftime('%Y-%m-%d')
                ])

        print(f"[EXPORT] CSV exported: {filename}")
        return filename