
<h2 align="center">SKYOJ - 新一代 AI 驱动的在线评测系统</h2>

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

**SKYOJ** 是一个专为高校计算机教学与数据科学竞赛设计的现代化在线判题系统（Online Judge）。

不同于传统仅支持 ACM 模式的 OJ，SKYOJ 采用 **Vue3 + FastAPI + Docker** 微服务架构，创新性地引入了 **OOP 单元测试**与 **Kaggle 数据科学**评测模式。系统深度集成 **LLM（大语言模型）**，提供智能助教能力。

---

## 核心特性

### 1. 多模态评测体系 (Multi-Mode Judging)
打破传统算法题的局限，满足多元化教学需求：
- **ACM 经典模式**：基于标准输入输出（Std I/O）的比对，支持 C/C++、Java、Python 等主流语言。
- **OOP 面向对象模式**：支持上传 Test 脚本，对学生提交的类/方法进行黑盒测试，适合考察架构设计与封装能力。
- **Kaggle 数据科学模式**：支持大数据集处理与 CSV 结果比对，允许教师自定义评分脚本（如计算 RMSE, Accuracy），适用于机器学习课程。

### 2. AI 智能化增强 (AI-Powered)
- **AI 助教 (Smart Tutor)**：
  - 集成 **DeepSeek/OpenAI** 接口。
  - 采用 **CoT (思维链)** 与 **角色扮演** 提示词工程，引导学生分析逻辑漏洞，而非直接提供答案。

### 3. 企业级系统架构
- **云原生架构**：基于 Docker Compose 编排，实现 Web 服务、数据库、评测沙箱的完全解耦。
- **异步评测调度**：采用 RabbitMQ + Celery `solo` Worker，Web API 只保存任务和 Outbox 记录；判题、AI 和文件处理分别由单进程串行 Worker 执行，需要扩容时增加 Worker 容器数量。
- **安全沙箱隔离**：
  - **网络熔断**：容器配置 `network_mode="none"`，阻断恶意联网。
  - **资源配额**：基于 Linux Cgroups 严格限制 CPU、内存及 PID 数，防止 Fork 炸弹与资源耗尽攻击。

---
## 技术栈

| 模块 | 技术选型 | 说明 |
| :--- | :--- | :--- |
| **前端** | Vue 3 + Vite | 配合 Monaco Editor 实现 IDE 级编码体验 |
| **后端** | FastAPI (Python) | 高性能 ASGI RESTful API，SQLAlchemy ORM |
| **网关** | Nginx | 反向代理、负载均衡、静态资源加速 |
| **数据库** | MySQL 8.0 | 事务支持，存储用户数据与提交记录 |
| **消息队列** | RabbitMQ + Celery | 任务通知、可靠投递与串行 Worker |
| **容器化** | Docker & Compose | 全栈容器化部署，沙箱环境构建 |
| **LLM SDK** | OpenAI / DeepSeek | 智能助教推理服务 |

---

## 项目结构

```text
SKYOJ/
├── backend/                # FastAPI 后端业务逻辑
│   └── app/                # API 接口与模型定义
├── frontend/               # Vue3 前端源代码
├── docker/                 # 全部 Docker 配置（唯一目录）
│   ├── backend/            # 后端容器 Dockerfile
│   ├── frontend/           # 前端容器 Dockerfile
│   ├── runner/             # 判题沙箱镜像 (skyoj-runner)
│   ├── generator/          # 测试数据生成镜像 (skyoj-generator)
│   ├── mysql/              # MySQL 初始化脚本
│   └── nginx/              # Nginx 反向代理配置
├── docker-compose.yml      # 容器编排配置
├── .env.example            # 环境变量模板
└── README.md               # 项目说明文档
```

### 异步任务进程

系统只保留 `judge`、`ai`、`file` 三个队列。API 入队时把任务写入 MySQL 并直接向 RabbitMQ 发布任务 ID；Worker 使用 `--pool=solo --concurrency=1`，不在进程内创建线程池。判题 Worker 是唯一挂载 Docker Socket 的服务，`job-recovery` 进程负责回收租约过期的任务并重新投递。

---

## 快速开始 (Deployment)

本项目支持一键容器化部署。请确保本地已安装 **Git** 和 **Docker Desktop**。

### 第一步：获取代码

```bash
git clone https://github.com/TianyaSKY/SKYOJ.git
cd SKYOJ
```

### 第二步：配置环境变量

```bash
cp .env.example .env
```

请至少配置以下 LLM 变量（用于 AI 助教与测试数据生成）：

- `LLM_API_URL`
- `LLM_MODEL_NAME`
- `LLM_API_KEY`

同时必须把 `MYSQL_ROOT_PASSWORD`、`MYSQL_PASSWORD` 和 `SECRET_KEY` 替换为本地生成的强随机值；`DATABASE_URL` 使用非 root 的 `MYSQL_USER` 账号。仓库不会为这些变量提供可用默认值。

公开注册只创建学生账号。需要教师账号时，在后端容器中执行：

```bash
docker compose exec backend python scripts/create_teacher.py
```

### 第三步：构建沙箱镜像 (关键)

为了保证评测环境的安全性与独立性，需先构建判题 / 测例生成沙箱镜像。

**推荐：使用一键脚本**

```bash
# Linux / macOS
chmod +x scripts/build-sandbox.sh
./scripts/build-sandbox.sh

# Windows (cmd / PowerShell)
scripts\build-sandbox.bat
```

可选参数：

```bash
./scripts/build-sandbox.sh runner          # 仅判题沙箱 skyoj-runner
./scripts/build-sandbox.sh generator       # 仅测例沙箱 skyoj-generator
./scripts/build-sandbox.sh --no-cache      # 强制无缓存重建
```

**或手动构建：**

```bash
# 1. 构建判题运行环境镜像 (包含 GCC, Python, Java 环境)
docker build -t skyoj-runner ./docker/runner

# 2. 构建测试数据生成镜像
docker build -t skyoj-generator ./docker/generator
```

### 第四步：启动服务

使用 Docker Compose 拉起全栈服务：

```bash
# 后台启动所有服务
docker-compose up -d --build
```

### 第五步：访问系统

等待约 30 秒（数据库初始化）后访问：

* **前端页面**：http://localhost
* **后端 API**：http://localhost/api
* **数据库管理**：(如配置了 phpMyAdmin) http://localhost:8080

---

## 本地开发启动 (Local Development)

不想用 Docker 跑全栈时，可以按下面方式在本地逐个启动进程。所有命令在仓库根目录执行，需要 `uv`（Python 3.12）与 Node.js 20+。

### 安装依赖

```bash
# 后端依赖（根目录 pyproject.toml + uv.lock）
uv sync

# 前端依赖
cd frontend && npm install && cd ..
```


### 启动（MySQL + RabbitMQ + 全部 Worker）

mysql 与 rabbitmq 已映射到宿主机 `127.0.0.1`（仅本机可访问），先启动基础设施容器，再在本地逐个起进程：

```bash
# 终端 0：基础设施（仅 mysql + rabbitmq）
docker compose up -d mysql rabbitmq
```

```bash
# 终端 1：后端 API（密码必须是 docker compose 启动时 MYSQL_PASSWORD 的实际值）
cd backend
DATABASE_URL=mysql+pymysql://skyoj:replace_with_strong_app_password@127.0.0.1:3306/oj_db \
SECRET_KEY=hajimiyounanbeiluduoxixigahaayoudingdongji \
CELERY_BROKER_URL=amqp://guest:guest@127.0.0.1:5672// \
uv run python run.py
```

```bash
# 终端 2：判题 Worker（需先构建沙箱镜像：./scripts/build-sandbox.sh）
cd backend
uv run celery -A app.messaging.celery_app:celery_app worker --queues=judge --pool=solo --concurrency=1
```

```bash
# 终端 3：AI Worker
cd backend
uv run celery -A app.messaging.celery_app:celery_app worker --queues=ai --pool=solo --concurrency=1
```

```bash
# 终端 4：文件 Worker
cd backend
uv run celery -A app.messaging.celery_app:celery_app worker --queues=file --pool=solo --concurrency=1
```

```bash
# 终端 5：任务恢复器（兜底：重新投递消息丢失/超时的任务，建议常驻）
cd backend
uv run python -m app.workers.job_recovery
```

```bash
# 终端 6：前端
cd frontend
npm run dev
```

### 运行测试

```bash
uv run python -m pytest -q backend/tests
```

> 说明：测试固定使用 SQLite 内存库与 `memory://` broker（conftest 注入），不依赖外部服务；本地 `run.py` 依赖 `DATABASE_URL` / `SECRET_KEY` / `CELERY_BROKER_URL` 三个环境变量，缺失会拒绝启动。若提示 `[Errno 98] address already in use`，说明已有后端实例占用 5000 端口，先执行 `fuser -k 5000/tcp` 再启动；`DATABASE_URL` 中的密码必须是 MySQL 实际口令，不能是中文占位符。

---

## 系统截图

![problem-detail-editor.png](images/problem-detail-editor.png)
![homepage-landing.png](images/homepage-landing.png)
![public-datasets.png](images/public-datasets.png)
![problem-list.png](images/problem-list.png)
![teacher-dashboard.png](images/teacher-dashboard.png)
![submission-result.png](images/submission-result.png)
![admin-problem-management.png](images/admin-problem-management.png)

---

## 开发与贡献

**开发周期**: 2025.12.21 - 25

本项目是 **大连海洋大学信息工程学院** 本科生课程项目成果。欢迎提交 Issue 或 Pull Request 进行改进。

## 开源协议

本项目采用 [MIT License](https://opensource.org/licenses/MIT) 开源。
