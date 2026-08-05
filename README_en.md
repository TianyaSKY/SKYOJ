
<h2 align="center">SKYOJ - Next-Generation AI-Powered Online Judge System</h2>

<p align="center">
  <a href="README.md">中文</a> |
  <a href="README_en.md">English</a>
</p>

![hero-banner.png](images/hero-banner.png)
<div align="center">
  <img src="https://img.shields.io/badge/Vue-3.x-4FC08D?style=flat-square&logo=vue.js" alt="Vue3">
  <img src="https://img.shields.io/badge/FastAPI-0.x-009688?style=flat-square&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Docker-Enabled-2496ED?style=flat-square&logo=docker" alt="Docker">
  <img src="https://img.shields.io/badge/AI-Powered-purple?style=flat-square" alt="AI">
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License">
</div>

<br/>

**SKYOJ** is a modern Online Judge system designed for university computer science education and data science competitions.

Unlike traditional OJs that only support ACM mode, SKYOJ adopts a **Vue3 + FastAPI + Docker** microservice architecture and innovatively introduces **OOP Unit Testing** and **Kaggle Data Science** evaluation modes. The system deeply integrates **LLM (Large Language Models)** to provide smart tutoring capabilities.

---

## Core Features

### 1. Multi-Mode Judging
Breaks the limitations of traditional algorithm problems to meet diverse teaching needs:
- **ACM Classic Mode**: Comparison based on standard input/output (Std I/O), supporting mainstream languages like C/C++, Java, and Python.
- **OOP Object-Oriented Mode**: Supports uploading Test scripts for black-box testing of classes/methods submitted by students, suitable for assessing architectural design and encapsulation.
- **Kaggle Data Science Mode**: Supports large dataset processing and CSV result comparison, allowing teachers to customize scoring scripts (e.g., calculating RMSE, Accuracy), suitable for machine learning courses.

### 2. AI-Powered Enhancements
- **Smart Tutor**:
  - Integrated **DeepSeek/OpenAI** interfaces.
  - Employs **CoT (Chain of Thought)** and **Role-Playing** prompt engineering to guide students in analyzing logical flaws rather than providing direct answers.

### 3. Enterprise-Grade Architecture
- **Cloud-Native Architecture**: Orchestrated based on Docker Compose, achieving complete decoupling of Web services, databases, and evaluation sandboxes.
- **Asynchronous Evaluation Scheduling**: Uses RabbitMQ and Celery `solo` workers. The API persists jobs and publishes task IDs to RabbitMQ directly at enqueue time, while dedicated single-process workers serially handle judging, AI, and file tasks; scale out by adding worker containers.
- **Security Sandbox Isolation**:
  - **Network Circuit Breaking**: Containers are configured with `network_mode="none"` to block malicious networking.
  - **Resource Quotas**: Strictly limits CPU, memory, and PID counts based on Linux Cgroups to prevent Fork bombs and resource exhaustion attacks.

---
![project-timeline-1.gif](images/project-timeline-1.gif)
![project-timeline-2.gif](images/project-timeline-2.gif)
## Tech Stack

| Module | Technology Selection | Description |
| :--- | :--- | :--- |
| **Frontend** | Vue 3 + Vite | IDE-level coding experience with Monaco Editor |
| **Backend** | FastAPI (Python) | High-performance ASGI RESTful API, SQLAlchemy ORM |
| **Gateway** | Nginx | Reverse proxy, load balancing, static resource acceleration |
| **Database** | MySQL 8.0 | Transaction support, storing user data and submission records |
| **Messaging** | RabbitMQ + Celery | Reliable task delivery and serial workers |
| **Containerization** | Docker & Compose | Full-stack containerized deployment, sandbox environment construction |
| **LLM SDK** | OpenAI / DeepSeek | Smart tutor inference service |

---

## Project Structure

```text
SKYOJ/
├── backend/                # FastAPI backend business logic
│   └── app/                # API interfaces and model definitions
├── frontend/               # Vue3 frontend source code
├── docker/                 # All Docker configs (single directory)
│   ├── backend/            # Backend container Dockerfile
│   ├── frontend/           # Frontend container Dockerfile
│   ├── runner/             # Judge sandbox image (skyoj-runner)
│   ├── generator/          # Test-data generation image (skyoj-generator)
│   ├── mysql/              # MySQL init script
│   └── nginx/              # Nginx reverse proxy config
├── docker-compose.yml      # Container orchestration configuration
├── .env.example            # Environment variable template
└── README.md               # Project documentation
```

### Asynchronous task processes

The system keeps only the `judge`, `ai`, and `file` queues. At enqueue time the API persists the job in MySQL and publishes the task ID to RabbitMQ directly. Workers run with `--pool=solo --concurrency=1`; no in-process thread pool is used. The Judge Worker is the only service that mounts the Docker Socket, and the `job-recovery` process re-publishes tasks whose lease has expired.

---

## Quick Start (Deployment)

This project supports one-click containerized deployment. Please ensure **Git** and **Docker Desktop** are installed locally.

### Step 1: Get the Code

```bash
git clone https://github.com/TianyaSKY/SKYOJ.git
cd SKYOJ
```

### Step 2: Configure Environment Variables

```bash
cp .env.example .env
```

Please configure at least these LLM variables (for AI tutor and test-data generation):

- `LLM_API_URL`
- `LLM_MODEL_NAME`
- `LLM_API_KEY`

You must also replace `MYSQL_ROOT_PASSWORD`, `MYSQL_PASSWORD`, and `SECRET_KEY` with strong locally generated values, and keep `DATABASE_URL` pointed at the non-root `MYSQL_USER` account. The repository does not provide usable defaults for these values.

Public registration creates student accounts only. Create a teacher account interactively inside the backend container:

```bash
docker compose exec backend python scripts/create_teacher.py
```

### Step 3: Build Sandbox Images (Critical)

To ensure the security and independence of the evaluation environment, build the judging and test-data generation sandbox images first.

**Recommended: one-click scripts**

```bash
# Linux / macOS
chmod +x scripts/build-sandbox.sh
./scripts/build-sandbox.sh

# Windows (cmd / PowerShell)
scripts\build-sandbox.bat
```

Optional flags:

```bash
./scripts/build-sandbox.sh runner          # only skyoj-runner
./scripts/build-sandbox.sh generator       # only skyoj-generator
./scripts/build-sandbox.sh --no-cache      # force rebuild without cache
```

**Or build manually:**

```bash
# 1. Build the judging runtime environment image (includes GCC, Python, Java)
docker build -t skyoj-runner ./docker/runner

# 2. Build the test data generation image
docker build -t skyoj-generator ./docker/generator
```
### Step 4: Start Services

Use Docker Compose to pull up the full-stack services:

```bash
# Start all services in the background
docker-compose up -d --build
```

### Step 5: Access the System

Wait about 30 seconds (database initialization) and then access:

* **Frontend Page**: http://localhost
* **Backend API**: http://localhost/api
* **Database Management**: (if phpMyAdmin is configured) http://localhost:8080

---

## Local Development

To develop without Docker, start each process locally from the repository root. You need `uv` (Python 3.12) and Node.js 20+.

### Install Dependencies

```bash
# Backend (root pyproject.toml + uv.lock)
uv sync

# Frontend
cd frontend && npm install && cd ..
```

### Minimal Startup (API + SQLite, no message queue)

Good for frontend/API-only work without judging tasks:

```bash
# Terminal 1: backend API (port 5000)
cd backend
DATABASE_URL=sqlite:///./skyoj.db SECRET_KEY=dev-only-secret-change-me CELERY_BROKER_URL=memory:// uv run python run.py
```

```bash
# Terminal 2: frontend dev server (port 5173, /api proxied to 5000)
cd frontend
npm run dev
```

### Full Local Setup (MySQL + RabbitMQ + all Workers)

Start the infrastructure containers, then run each process locally (`config.py` rewrites `@mysql:` to `@127.0.0.1:` in `DATABASE_URL` automatically; change the host in `CELERY_BROKER_URL` to `127.0.0.1` yourself):

```bash
# Terminal 0: infrastructure (mysql + rabbitmq only)
docker compose up -d mysql rabbitmq
```

```bash
# Terminal 1: backend API (or configure via .env, which config.py loads)
cd backend
DATABASE_URL=mysql+pymysql://skyoj:your_password@127.0.0.1:3306/oj_db \
SECRET_KEY=replace_with_strong_value \
CELERY_BROKER_URL=amqp://guest:guest@127.0.0.1:5672// \
uv run python run.py
```

```bash
# Terminal 2: Judge worker (build sandbox images first: ./scripts/build-sandbox.sh)
cd backend
uv run celery -A app.messaging.celery_app:celery_app worker --queues=judge --pool=solo --concurrency=1
```

```bash
# Terminal 3: AI worker
cd backend
uv run celery -A app.messaging.celery_app:celery_app worker --queues=ai --pool=solo --concurrency=1
```

```bash
# Terminal 4: File worker
cd backend
uv run celery -A app.messaging.celery_app:celery_app worker --queues=file --pool=solo --concurrency=1
```

```bash
# Terminal 5 (optional): job recovery (re-publishes tasks with expired leases)
cd backend
uv run python -m app.workers.job_recovery
```

```bash
# Terminal 6: frontend
cd frontend
npm run dev
```

### Running Tests

```bash
uv run python -m pytest -q backend/tests
```

> Note: tests always use an in-memory SQLite database and the `memory://` broker (injected by conftest) and need no external services. Local `run.py` requires `DATABASE_URL`, `SECRET_KEY`, and `CELERY_BROKER_URL` and refuses to start without them.

---

## System Screenshots

![problem-detail-editor.png](images/problem-detail-editor.png)
![homepage-landing.png](images/homepage-landing.png)
![public-datasets.png](images/public-datasets.png)
![problem-list.png](images/problem-list.png)
![teacher-dashboard.png](images/teacher-dashboard.png)
![submission-result.png](images/submission-result.png)
![admin-problem-management.png](images/admin-problem-management.png)

---

## Development and Contribution

**Development Period**: 2025.12.21 - 25

This project is a result of an undergraduate course project at the **School of Information Engineering, Dalian Ocean University**. Issues or Pull Requests for improvements are welcome.

## License

This project is open-sourced under the [MIT License](https://opensource.org/licenses/MIT).
