
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

Unlike traditional OJs that only support ACM mode, SKYOJ adopts a **Vue3 + FastAPI + Docker** microservice architecture and innovatively introduces **OOP Unit Testing** and **Kaggle Data Science** evaluation modes. The system deeply integrates **LLM (Large Language Models)** and **Deep Learning Vector Models**, achieving a comprehensive intelligent assistant from "code plagiarism detection" to "smart tutoring."

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
- **Semantic Plagiarism Detection**:
  - Abandons traditional text edit distance algorithms.
  - Built-in fine-tuned **Sentence-Transformers (UnixCoder)** model.
  - Converts code into high-dimensional semantic vectors to effectively identify "variable renaming," "statement reordering," and other obfuscation techniques, with a similarity recognition accuracy > 0.85.

### 3. Enterprise-Grade Architecture
- **Cloud-Native Architecture**: Orchestrated based on Docker Compose, achieving complete decoupling of Web services, databases, and evaluation sandboxes.
- **Asynchronous Evaluation Scheduling**: Uses a non-blocking task distribution mechanism. The Web main thread only handles requests, while background daemon thread pools handle time-consuming judging, ensuring system stability under high concurrency.
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
| **Containerization** | Docker & Compose | Full-stack containerized deployment, sandbox environment construction |
| **AI Model** | Sentence-Transformers | Semantic vector calculation for plagiarism detection |
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

### Step 3: Build Sandbox Images (Critical)

To ensure the security and independence of the evaluation environment, basic evaluation images must be built manually:

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
* **Backend API**: http://localhost:5000/api
* **Database Management**: (if phpMyAdmin is configured) http://localhost:8080

---

## System Screenshots

![problem-detail-editor.png](images/problem-detail-editor.png)
![homepage-landing.png](images/homepage-landing.png)
![public-datasets.png](images/public-datasets.png)
![problem-list.png](images/problem-list.png)
![plagiarism-log-list.png](images/plagiarism-log-list.png)
![teacher-dashboard.png](images/teacher-dashboard.png)
![plagiarism-code-compare.png](images/plagiarism-code-compare.png)
![submission-result.png](images/submission-result.png)
![admin-problem-management.png](images/admin-problem-management.png)

---

## Development and Contribution

**Development Period**: 2025.12.21 - 25

This project is a result of an undergraduate course project at the **School of Information Engineering, Dalian Ocean University**. Issues or Pull Requests for improvements are welcome.

## License

This project is open-sourced under the [MIT License](https://opensource.org/licenses/MIT).

