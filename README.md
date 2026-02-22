# PlagCheck — Plagiarism Detection System

A full-stack plagiarism detection web application built with **FastAPI**, **SQLAlchemy**, and a pure-CSS frontend. Supports three role-based portals (Student, Teacher, Admin), TF-IDF cosine-similarity comparison across submissions, and a live Google web search to cross-check content against the internet.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started (Local)](#getting-started-local)
- [Environment Variables](#environment-variables)
- [Default Admin Credentials](#default-admin-credentials)
- [Role Workflow](#role-workflow)
- [Test Data](#test-data)
- [Deployment](#deployment)
- [API Reference](#api-reference)

---

## Features

| Feature | Details |
|---------|---------|
| **Role-based access** | Admin / Teacher / Student portals, JWT cookie auth |
| **Assignment submission** | Upload `.txt`, `.pdf`, or `.docx` files |
| **TF-IDF plagiarism engine** | Cosine-similarity comparison across all same-course submissions |
| **Auto-grading** | Submissions that breach the threshold are automatically scored 0 |
| **Google web search** | Top-5 Google results checked against submission content |
| **Teacher dashboard** | Upload question files, set due dates, grade submissions |
| **Admin panel** | Create / edit / delete users, reset passwords, change admin password |
| **Modern UI** | CSS design system, no framework dependency, fully responsive |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI 0.109, Python 3.11+ |
| ORM | SQLAlchemy 2.0 |
| Database | MySQL (Aiven Cloud) |
| Auth | JWT (python-jose) + bcrypt |
| Templates | Jinja2 |
| NLP | scikit-learn (TF-IDF + cosine similarity), NLTK |
| File parsing | PyPDF2, python-docx |
| Web search | googlesearch-python |
| Server | Uvicorn (ASGI) |

---

## Project Structure

```
Plagiarism-Detector/
├── app/
│   ├── api/v1/
│   │   ├── auth.py          # JSON API: login, register, /me
│   │   ├── common.py        # Public pages: /, /login, /register, /logout
│   │   ├── student.py       # /student/* routes
│   │   ├── teacher.py       # /teacher/* routes
│   │   └── admin.py         # /admin/* routes
│   ├── core/
│   │   ├── config.py        # Settings (reads from .env)
│   │   ├── deps.py          # Auth dependencies
│   │   ├── security.py      # JWT helpers, password hashing
│   │   └── exceptions.py    # Custom HTTP exceptions
│   ├── db/
│   │   ├── database.py      # SQLAlchemy engine + session
│   │   ├── models.py        # ORM models (User, Assignment, …)
│   │   └── schemas.py       # Pydantic schemas
│   ├── services/
│   │   ├── plagiarism_service.py  # TF-IDF engine + Google search
│   │   ├── assignment_service.py  # Assignment CRUD logic
│   │   └── user_service.py        # User CRUD logic
│   ├── utils/
│   │   ├── file_utils.py    # PDF/DOCX/TXT → plain text
│   │   └── text_processing.py     # Preprocessing, stemming, stopwords
│   └── main.py              # FastAPI app entry point
├── templates/
│   ├── base.html            # Master layout + CSS design system
│   ├── index.html           # Landing page
│   ├── login.html
│   ├── register.html        # Auto-generated username
│   ├── student/             # dashboard.html, result.html
│   ├── teacher/             # dashboard, submissions, plagiarism_report, grade, …
│   └── admin/               # dashboard, update_user, reset_password
├── static/
│   └── Images/
├── TestData/                # Sample files for manual testing (see below)
│   ├── AssignmentQuestion.pdf
│   ├── AssignmentA.docx
│   ├── AssignmentB.txt
│   └── AssignmentC.pdf
├── .env.example             # Copy to .env and fill in values
├── requirements.txt
└── Procfile                 # For Railway / Heroku
```

---

## Getting Started (Local)

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/Plagiarism-Detector.git
cd Plagiarism-Detector
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Open .env and fill in your DATABASE_URL, SECRET_KEY, etc.
```

### 5. Run the development server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000** in your browser.

---

## Environment Variables

Copy `.env.example` to `.env` and set the following:

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Full SQLAlchemy connection string | `mysql+pymysql://user:pass@host:port/db` |
| `SECRET_KEY` | Random 32+ char string for JWT signing | `openssl rand -hex 32` |
| `ADMIN_USERNAME` | Username for the default admin account | `admin` |
| `ADMIN_PASSWORD` | Password for the default admin account | `changeme` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT cookie lifetime | `1440` (24 h) |
| `DEBUG` | Enable debug mode | `false` |

> **Never commit your real `.env` to Git.** It is listed in `.gitignore`.

---

## Default Admin Credentials

On first startup the app automatically creates an admin user:

| Field | Default value |
|-------|---------------|
| Username | `admin` |
| Password | `admin123` |

Change these immediately in your `.env` file before deploying.

---

## Role Workflow

```
Teacher                              Student
  │                                     │
  ├─ Upload question file (PDF/DOCX)    │
  ├─ Set due date for course            │
  │                                     ├─ Register (Student role)
  │                                     ├─ Submit assignment file
  │                                     │
  ├─ View all submissions               │
  ├─ Run plagiarism check ──────────────┘
  │    ├─ TF-IDF vs other submissions
  │    └─ Google top-5 web results
  ├─ View full plagiarism report
  └─ Grade submission (marks + comment)
                                         │
                                         └─ Student views result + score
```

---

## Test Data

The `TestData/` folder contains ready-made files for a full end-to-end demo:

| File | Purpose | How to use |
|------|---------|------------|
| `AssignmentQuestion.pdf` | Sample question file | Upload as Teacher via **Create Assignment** → the course code must match the students' course |
| `AssignmentA.docx` | Student submission — contains unique content **and** the shared sentence | Login as a Student and submit via the dashboard |
| `AssignmentB.txt` | Student submission — contains the **same shared sentence** as A (triggers match) | Login as a second Student and submit |
| `AssignmentC.pdf` | Student submission — contains content sourced from Wikipedia (triggers Google web hit) | Login as a third Student and submit |

### Suggested test sequence

1. **Register three student accounts** — all with the same course code (e.g. `CS`)
2. **Register one teacher account** with the same course code `CS`
3. **Login as Teacher** → *Create Assignment* → upload `AssignmentQuestion.pdf`, set threshold to `30%`
4. **Set a due date** from the Teacher dashboard
5. **Login as each student** and submit their respective file from `TestData/`
6. **Back as Teacher** → *Submissions* → click **Plagiarism** on any submission
7. View the report: AssignmentA and AssignmentB should show a cross-match; AssignmentC should show Google web results
8. **Grade** any submission — mark is saved and visible to the student

---

## Deployment

### Option 1 — Railway (recommended, free tier)

1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
3. Add the environment variables listed above under **Variables**
4. Railway auto-detects the `Procfile` and starts the server

### Option 2 — Render

1. Push to GitHub
2. [render.com](https://render.com) → **New Web Service** → connect repo
3. **Build command:** `pip install -r requirements.txt`
4. **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables in the Render dashboard

### Option 3 — Heroku

```bash
heroku create your-app-name
heroku config:set DATABASE_URL="mysql+pymysql://..."
heroku config:set SECRET_KEY="your-secret-key"
git push heroku main
```

### Option 4 — Vercel (serverless)

A `vercel.json` is included. Run:

```bash
npm i -g vercel
vercel --prod
```

> **Note:** Vercel is serverless — long-running requests (plagiarism check with Google search) may hit the 10-second timeout on the free plan. Railway or Render are better fits for this workload.

---

## API Reference

All JSON API endpoints are under `/api/v1/`:

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/auth/register` | — | Register a new user |
| `POST` | `/api/v1/auth/login` | — | Login, returns JWT |
| `GET` | `/api/v1/auth/me` | JWT | Current user info |
| `GET` | `/admin/users` | Admin | List all users |
| `POST` | `/admin/users` | Admin | Create user |
| `PUT` | `/admin/users/{id}` | Admin | Update user |
| `DELETE` | `/admin/users/{id}` | Admin | Delete user |
| `GET` | `/student/api/assignments` | Student | Student's assignments |
| `GET` | `/teacher/api/assignments` | Teacher | Course assignments |

Page routes (HTML) follow the pattern `/student/*`, `/teacher/*`, `/admin/*`.

---

## License

MIT — free for personal and commercial use.
