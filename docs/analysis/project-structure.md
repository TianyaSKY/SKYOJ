# SKYOJ 项目结构分析

> 评估基准：仓库 `master` 分支（commit `b253d14` 截至）的工作树。
> 工作区在 `e:/PycharmProjects/SKYOJ`，所有结论都对照实际文件路径与行号。

## 1. 仓库总览

```
SKYOJ/
├── backend/                # FastAPI 后端（Python 3.12 + uv 管理）
│   ├── app/                # 业务代码
│   ├── tests/              # pytest 测试（19 个文件）
│   ├── uploads/            # 题目测试数据/头像等文件存储
│   ├── pytest.ini
│   └── run.py
├── frontend/               # Vue3 + Vite
│   └── src/
├── docker/                 # 全部容器定义（唯一编排根）
│   ├── backend/Dockerfile
│   ├── frontend/Dockerfile
│   ├── runner/             # skyoj-runner 判题沙箱镜像
│   ├── generator/          # skyoj-generator 测例沙箱镜像
│   ├── mysql/init.sql
│   └── nginx/default.conf
├── docker-compose.yml      # 6 个服务
├── docs/
│   └── security-debt.md    # 已知安全债务（已过期，需更新）
├── scripts/                # 沙箱构建脚本（Windows/Linux）
├── pyproject.toml          # 后端依赖与 uv 锁定
├── .env.example
├── .github/workflows/ci.yml
├── AGENTS.md               # 项目协作规范
└── README.md
```

## 2. 技术栈速览

| 层 | 选型 | 关键证据 |
|---|---|---|
| Web 框架 | FastAPI 0.141 | `pyproject.toml:11`、`backend/app/main.py:73` |
| ORM | SQLAlchemy 2.0 | `pyproject.toml:22`、`backend/app/models/*.py` |
| 数据库 | MySQL 8.0（测试用 SQLite 内存） | `docker-compose.yml:3`、`backend/tests/conftest.py` |
| 异步队列 | RabbitMQ + Celery | `docker-compose.yml:30`、`messaging/celery_app.py` |
| 缓存/限流/PubSub | Redis 7 | `docker-compose.yml:50`、`utils/exam_cache.py`、`utils/realtime.py`、`middleware/rate_limit.py` |
| Web 鉴权 | JWT（HS256，PyJWT） | `utils/auth_tools.py`、`api/submission.py:41` |
| 密码哈希 | bcrypt 5 | `pyproject.toml:6`、`utils/passwords.py` |
| 沙箱 | Docker SDK 7.2 | `services/sandbox_runner.py` |
| 查重 | JPlag（外部 HTTP 服务） | `clients/jplag_client.py`（默认 `http://localhost:25678`） |
| LLM | OpenAI Python SDK 2.53（兼容 DeepSeek） | `clients/llm_client.py` |
| 前端 | Vue 3.5 + Vite 7 + Pinia 3 | `frontend/package.json` |
| 编辑器 | Monaco 0.55（@guolao/vue-monaco-editor） | `frontend/package.json:17` |
| UI | Element Plus 2.13 | `frontend/package.json:19` |
| 校验 | Zod 4.4（前端） | `frontend/package.json:29` |
| Markdown | markdown-it + marked + KaTeX | `frontend/package.json:21-24` |
| 日志 | Loguru | `pyproject.toml:13`（与 AGENTS.md 一致） |
| CI | GitHub Actions（3 jobs） | `.github/workflows/ci.yml` |

## 3. 后端分层

后端严格遵循 `AGENTS.md` 规定的 `api / domain / models / repositories / services / clients / tasks / messaging / middleware / utils` 分层，并新增了 `api/schemas/`（Pydantic 校验）、`workers/`（job_recovery）、`mappers.py`（ORM ↔ domain 集中映射）。

### 3.1 关键路径与职责

| 目录/文件 | 职责 |
|---|---|
| `app/main.py` | FastAPI 工厂；7 个业务异常映射 401/403/404/400/502/429；挂审计中间件 |
| `app/api/` | HTTP 路由（11 个模块：auth/dataset/debug/exam/llm/plagiarism/problem/search/submission/sys_dict/user） |
| `app/api/schemas/` | 各模块的 Pydantic 模型（11 个文件） |
| `app/domain/` | 业务参数与结果的 dataclass（`@dataclass(frozen=True)`，无 dict/None 滥用） |
| `app/models/` | SQLAlchemy ORM 模型（13 个表） |
| `app/mappers.py` | ORM → domain 集中映射（避免散落各处的字段拼装） |
| `app/repositories/` | 数据访问层（12 个 repository） |
| `app/services/` | 业务编排（20 个 service），含三个判题模式：`acm.py / oop.py / kaggle.py` |
| `app/services/sandbox_runner.py` | Docker 沙箱抽象（判题沙箱的所有调用都走这里） |
| `app/clients/` | 外部服务：`llm_client.py / jplag_client.py / *_storage_client.py` |
| `app/tasks/` | Celery 任务定义（`base.py` 提供 `run_job` 统一模板） |
| `app/workers/job_recovery.py` | 兜底：扫描过期租约、重新投递 |
| `app/messaging/` | Celery app + 队列名 + 任务名常量 |
| `app/middleware/` | `audit.py` 写操作审计 + `rate_limit.py` Redis 限流 |
| `app/utils/` | `realtime.py / exam_cache.py / auth_tools.py / api_response.py / sys_dict.py / time.py / files.py / passwords.py` |

### 3.2 队列与任务

三队列：`judge / ai / file`（`messaging/queues.py`），全部 `--pool=solo --concurrency=1`。

任务名（`messaging/task_names.py`）：
- `JUDGE_SUBMISSION_TASK` → judge
- `DEBUG_SUBMISSION_TASK` → judge
- `EXECUTE_TEST_DATA_TASK` → judge
- `GENERATE_PROBLEM_TASK` / `GENERATE_TEST_SCRIPT_TASK` → ai
- `FINALIZE_DATASET_TASK` → file
- `SCAN_PLAGIARISM_TASK` → judge（提交 Accepted 后自动触发）

### 3.3 异步任务流程（`AsyncJobService` + `AsyncJob` + `job_recovery`）

`refactor: drop transactional outbox, publish jobs directly at enqueue` 后流程：

1. API 写 `async_jobs` 行（task_name / queue / payload / dedupe_key / max_attempts）
2. 同一事务内 `celery_app.send_task(task_name, args=[job_id], queue=...)`（消息体只含 job_id）
3. Worker `run_job(job_id, task_name, handler)` → `start_job` 领取租约 → 执行 → `complete_job` / `fail_job`
4. `job_recovery` 进程常驻，`JOB_RECOVERY_INTERVAL_SECONDS`（默认 30s）扫描租约过期任务并重新投递
5. Celery `task_acks_late=True`、`task_reject_on_worker_lost=True` → Worker 崩溃自动重新投递

幂等键示例：`judge-submission:{id}`、`debug-submission:{id}`、`ai-draft:{id}`、`plagiarism-scan:{problem_id}`。

### 3.4 判题路径

- `api/submission.py:submit_code()` → 限流 10/60s → 写 submission 行 → `AsyncJobService.enqueue_judge_submission`
- Worker `judge_submission` → `services/judge_service.judge_submission` → 按 `problem.type` 分发：
  - `acm` → `services/acm.run_acm_judge`（ThreadPoolExecutor，每个测试点独立容器，最多 8 并发）
  - `oop` / `kaggle` → 对应 service
- 结果写回 DB → 实时推 Redis channel `skyoj:submission:{id}` → 失效考试排行榜缓存 → Accepted 后投递查重任务

### 3.5 沙箱隔离

- `docker/runner/Dockerfile` 是判题镜像，**只有 `judge-worker` 容器挂载 `/var/run/docker.sock`**（`docker-compose.yml:156`）
- 容器配置 `network_mode="none"`、Cgroups 限制 CPU/内存/PID（`acm.py:48-52`）
- API 进程不挂 docker.sock（**这与 `docs/security-debt.md` 的描述不一致，文档已过期**）

## 4. 前端结构

### 4.1 路由（`router/index.js`）

- 学生：`/problems /problem/:id /submission/:id /datasets /exam /exam/:id /exam/:id/rank /profile`
- 教师：`/admin/dashboard /admin/problems /admin/problems/:id/preview /admin/datasets /admin/drafts /admin/exams /admin/exams/:id/monitor /admin/submissions /admin/settings`
- 公共：`/login /register /docs/{acm,kaggle,oop,teacher-manual}`
- 路由守卫：未登录跳登录、教师访问学生视图跳管理视图、考试模式下锁定题目路由（需 `?exam_id=`）

### 4.2 视图（13 + 8）

- 顶层（13）：`HomeView / LoginView / RegisterView / ProblemListView / ProblemDetailView / SubmissionDetailView / ExamView / ExamDetailView / ExamRankView / ProfileView / DatasetListView`
- 教师后台（8）：`TeacherDashboardView / ProblemAdminView / ProblemPreviewView / ExamAdminView / ExamMonitorView / SubmissionAdminView / DraftBoxView / TeacherSettingsView`
- 文档（4）：`ACMDocView / OOPDocView / KaggleDocView / TeacherManualView`

### 4.3 组件

- 顶层（5）：`SubmissionHeatmap.vue`（提交热力图，已实现）/ `DebugResultPanel.vue`（ACM 单点调试抽屉）/ `MarkdownContentEditor.vue`（统一 Markdown 编辑/预览）
- `admin/`：`TeacherSidebar.vue`
- `layout/`：`AppLayout.vue / NavBar.vue`

### 4.4 工具与状态

- `utils/request.js`：axios + token 注入 + 登录态失效拦截
- `utils/websocket.js`：提交判题 WebSocket 客户端
- `utils/markdown.js`：Markdown 渲染入口
- `utils/featureFlags.js`：特性开关占位（commit `6492bcc` 恢复）
- `stores/sys.js / stores/user.js`：Pinia 全局状态

## 5. 数据模型（13 张表）

| 表 | 关键字段 | 备注 |
|---|---|---|
| `users` | username / password_hash / role(student/teacher) / avatar | role 仅 2 枚举，无班级/年级 |
| `problems` | type(acm/oop/kaggle) / language / time_limit / memory_limit / content / template_code / test_case_path | **无 tags / difficulty / knowledge_points** |
| `submissions` | status(Pending/Accepted/Wrong Answer/TLE/RE/CE/SE) / score / output_log / exam_id | 有 `ix_submissions_exam_problem_user`、`ix_submissions_created_at` |
| `exams` | start/end time / password(SHA-256) / is_visible / created_by | 单一考试模式（无 homework / contest 区分） |
| `exam_problems` | exam_id / problem_id / display_id / score | 关联表 |
| `datasets` | 文件型数据集 | 由 `FINALIZE_DATASET_TASK` 处理 |
| `ai_drafts` | task_type / status / request_payload / result_payload / consumed_at | AI 异步草稿箱 |
| `plagiarism_*` | 查重结果与匹配块 | 集成 JPlag |
| `async_jobs` | task_name / queue / payload / dedupe_key / attempts / lease_until | 替代了之前的 transactional outbox |
| `audit_log` | user_id / method / path / status_code / ip / user_agent / payload_summary | 由 `AuditMiddleware` 自动写入 |
| `sys_dict` | key / val | 系统级配置（标题/公告/练习开关） |
| `search_history` | user_id / keyword | 搜索历史 |
| `debug_runs` | 调试运行记录 | 由 `DEBUG_SUBMISSION_TASK` 处理 |

## 6. 工程实践现状

### 6.1 已落地

- **日志**：全栈 Loguru，禁用 `print` / `logging`
- **异常映射**：6 个业务异常 → 401/403/404/400/502/429 + 统一 `{"error": "..."}` 格式（`main.py:85-129`）
- **中间件**：审计 + 限流（写操作审计 / 登录注册提交限流）
- **测试**：19 个 pytest 文件，覆盖 service / mapper / auth / exam / async_job / queue architecture / judgeservice / llm client / search / submission / file services
- **CI**：lint（compileall）+ test + frontend build + docker compose validate
- **依赖管理**：`uv` 锁定（`uv.lock`），`pyproject.toml` 集中维护
- **代码规范**：遵循 AGENTS.md，注释/日志中文，标识符英文
- **判题优化**：ACM 并发独立容器（提交 `04c4221`）、排行榜 Redis 缓存（`c5c0080`）、N+1 优化（`031471d`）、移除死代码（`eddf7e5`）
- **实时**：WebSocket 判题结果推送（`1097cdc/3d9f9df`）
- **重构序列**（最近 30 次提交）：outbox → mapper → SandboxRunner 拆环 → run_job 统一模板 → judgeservice 编排 → 文档与一致性收口

### 6.2 缺口

- **前端测试**：无 Vitest、无 Vue Test Utils 配置（CI 只做 build，不跑测试）
- **E2E**：无 Playwright
- **前端错误处理**：`utils/request.js` 拦截 `code`，但后端 `main.py` 返回的是 `error` 字段，**格式不一致** → 登录失效提示永不触发
- **WebSocket 重连**：`utils/websocket.js:17` 声明了 `RECONNECT_DELAY_MS` 但代码未使用，断了不会自动重连
- **FastAPI 弃用 API**：`main.py:157` 使用 `on_event("startup")`，应改 `lifespan`
- **文档过期**：`docs/security-debt.md` 写"API 进程直接调用 Docker SDK"，但 `docker-compose.yml` 已只有 `judge-worker` 挂 docker.sock
- **Git 工作流**：所有提交直接进 `master`，没有 `feat/fix/refactor` 分支
- **可观测性**：无 Prometheus / Grafana / Loki，依赖 Loguru 的 stdout 日志
- **题库扩展**：无 `tags / difficulty / knowledge_points / discussion / solution / homework` 任何相关模型
- **判题模式**：仅 ACM/OOP/Kaggle，无 SPJ / 互动题 / 输出题 / OI 按点给分

## 7. 仓库度量（粗略）

- 后端 Python 文件：约 100+ 个（`app/` 与 `tests/` 合计），核心分层均单文件单模块
- 前端 Vue 文件：22 个视图 + 5 个顶层组件 + 2 个布局组件 + 8 个 api 模块 + 2 个 store + 4 个工具
- 路由：24 条
- API 路由：约 50 条（11 个 API 文件合计）
- Celery 任务：7 个
- Docker 服务：6 个（mysql / rabbitmq / redis / backend / job-recovery / judge-worker / ai-worker / file-worker / frontend — 实际 9 个）
