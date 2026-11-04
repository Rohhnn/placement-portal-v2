# Placement Portal (v2)

A decoupled placement management application with a Flask REST API backend and a Vue.js single-page frontend. Redis is used for response caching and as the Celery message broker.

## Overview

The domain covers institute administrators, companies, and students. Companies and students register through the API; companies and placement drives require admin approval. Companies create drives and manage applicant status. Students browse approved drives, apply, update profiles, and export application history asynchronously. Role-based JWT authentication protects API endpoints.

## Architecture

- **Backend**: Flask application factory with Blueprints for auth, admin, company, student, and job-status routes. Responses are JSON.
- **Frontend**: Vue.js 3 SPA (CDN) with Vue Router and Axios, served as a single `frontend/index.html`.
- **Auth**: JWT issued on login and validated via a `token_required` decorator; role checks restrict privileged routes.
- **Caching**: Flask-Caching with Redis (for example, admin dashboard responses).
- **Background jobs**: Celery with Redis — daily deadline reminders, monthly HTML placement reports, and on-demand CSV export of a student's applications.

## Domain model

The schema is as follows:

| Entity | Purpose |
|--------|---------|
| `User` | Credentials and role (`admin`, `company`, `student`) |
| `Company` | Company profile; approval and blacklist flags |
| `Student` | Student profile and resume path |
| `PlacementDrive` | Company job posting with approval/lifecycle status |
| `Application` | Student–drive application with status tracking |

## Tech stack

- Flask, Flask-SQLAlchemy, Flask-RESTful patterns via Blueprints, Flask-Caching, flask-cors
- PyJWT
- Vue.js 3, Vue Router 4, Axios, Bootstrap 5 (CDN)
- SQLite
- Redis (cache + Celery broker/backend)
- Celery (including Celery Beat schedules)

## Project structure

```
.gitignore
README.md
requirements.txt
backend/
  app.py               # Application factory
  models.py            # SQLAlchemy models
  config.py            # Configuration
  extensions.py        # db and cache
  celery_worker.py     # Celery app and tasks
  routes/
    __init__.py
    auth.py
    admin.py
    company.py
    student.py
    jobs.py
frontend/
  index.html           # Vue SPA
  src/main.js
static/
  uploads/             # Resume uploads (contents ignored)
  exports/             # CSV exports (contents ignored)
  reports/             # Generated monthly reports (contents ignored)
```

## Setup

Prerequisites: Python 3, Redis running locally (for example Memurai on Windows).

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

Start Redis, then in separate terminals:

```bash
# API / SPA (default port 5001)
python -m backend.app

# Celery worker
celery -A backend.celery_worker.celery_app worker --loglevel=info

# Celery Beat (scheduled tasks)
celery -A backend.celery_worker.celery_app beat --loglevel=info
```

Open the URL printed by the Flask process. A default admin account is seeded on first run (`admin` / `admin123`). Change this credential before any non-local use.

## Course Context

This repository contains the course project submitted for **Modern Application Development II** (Application Development 2) at IIT Madras, January 2026 term. It extends the placement portal domain from Application Development 1 into a REST API and Vue.js SPA architecture with Redis caching and Celery background jobs.
