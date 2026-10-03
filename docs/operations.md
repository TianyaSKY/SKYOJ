# SKYOJ 部署与运维手册

本文档面向希望自行把 SKYOJ 全栈跑起来的开发者 / 运维 / 教师。
本手册基于「全栈跑起来 + P0/P1/D/E 项已合并」快照，命令与文件路径均以
仓库根目录 `e:/PycharmProjects/SKYOJ` 为基准。

## 1. 一键启动

### 1.1 先决条件

| 软件       | 版本       | 备注                            |
|------------|------------|---------------------------------|
| Docker     | 24+        | 含 docker-compose plugin        |
| Node       | 20.19+     | 仅前端开发 / Vitest 需要         |
| Python     | 3.12+      | 后端 / 测试                      |
| Git        | 2.30+      | 推荐配置 LFS 与 CRLF/LF 规范      |

### 1.2 拉取代码与配置

```bash
git clone https://example.com/skyoj.git   # 或解压已分发 zip
cd SKYOJ

# 复制示例配置 → 真实 .env（脚本会自动生成强随机 SECRET_KEY / MYSQL_PASSWORD / RABBITMQ_PASS）
cp .env.example .env

# 如需手动重置密码，可在 PowerShell 中运行：
# python .tmp_gen_env.py  (本仓库 git 历史中可见一次性脚本)
```

`.env` 默认字段：

- `MYSQL_DATABASE=oj_db`
- `MYSQL_USER=skyoj`
- `MYSQL_PASSWORD=<随机 24 位>`
- `MYSQL_ROOT_PASSWORD=<随机 32 位>`
- `FRONTEND_PORT=80`
- `SECRET_KEY=<随机 48 位>`
- `DATABASE_URL=mysql+pymysql://skyoj:<password>@mysql:3306/oj_db`
- `RABBITMQ_DEFAULT_PASS=<随机 16 位>`
- `LLM_*`：用户自有 token（OpenAI 兼容 API）。

### 1.3 构建 sandbox 镜像（判题 / 测例生成）

`sandbox` 镜像不在 docker-compose.yml 中（出于安全隔离考虑），
需手动构建：

```bash
# Windows / PowerShell
.\scripts\build-sandbox.bat

# Linux / macOS
bash scripts/build-sandbox.sh
```

构建完成后可用：

```bash
docker images skyoj-runner skyoj-generator
```

### 1.4 启动全栈

```bash
docker compose up -d --build
docker compose ps    # 期望全部 9 个服务 healthy
curl http://localhost:5000/healthz   # 期望 {"status":"ok"}
```

#### 9 个服务一览

| 容器名              | 端口    | 作用                                                |
|---------------------|---------|-----------------------------------------------------|
| `skyoj-mysql`       | 3306    | MySQL 8，单库 `oj_db`                              |
| `skyoj-rabbitmq`    | 5672    | RabbitMQ，celery 任务队列（celery / ai / file）     |
| `skyoj-redis`       | 6379    | Redis，题面 Markdown 缓存 + Pub/Sub + 限流        |
| `skyoj-backend`     | 5000    | FastAPI，对外 HTTP API（Vue 前端走 nginx 转发）     |
| `skyoj-judge-worker`| -       | 判题 worker，**唯一挂载 docker.sock**              |
| `skyoj-ai-worker`   | -       | AI 出题 / 测例生成 worker                         |
| `skyoj-file-worker` | -       | 文件处理 worker                                   |
| `skyoj-job-recovery`| -       | 定时将 RabbitMQ 中未完成的超时任务回滚               |
| `skyoj-frontend`    | 80/8080 | nginx + Vue 静态资源                              |

### 1.5 一键停服 / 重启

```bash
docker compose down                 # 停服（保留 volumes）
docker compose down -v              # 停服并清空数据（慎用）
docker compose restart backend      # 仅重启后端
```

---

## 2. 数据初始化与账号

### 2.1 数据库自动建表 + 字典种子

`init_db()` 在 backend 容器启动时自动执行：

- `Base.metadata.create_all()` — 创建缺失的 ORM 表，保留已有表和数据。
- 若 `sys_dict` 表为空，按 `app/utils/sys_dict.py` 中默认值写入。
- 失败重试 5 次，每次间隔 3s（应对 mysql 慢启动）。

### 2.2 第一个教师账号

仓库提供了 `backend/scripts/create_teacher.py`，可创建默认教师用户：

```bash
docker exec -it skyoj-backend python scripts/create_teacher.py
```

请在生产环境**修改默认密码**。

---

## 3. 故障排查（FAQ）

### 3.1 backend 启动报 `PlagiarismService not defined`

- 原因：`app/api/deps.py` 没在顶层 import。
- 修复：本仓库 `fix/backend-imports-and-error-envelope` 分支已合并。
  请确保 master 分支包含该提交。

### 3.2 提交后状态一直 `Pending`

排查步骤：

1. 确认 judge-worker / file-worker 容器均为 healthy。
2. `docker logs skyoj-judge-worker --tail 30` 看是否有「判题业务执行异常」。
3. 检查 sandbox 镜像是否构建：`docker images skyoj-runner`。
4. `/api/submissions/{id}` 的 `case_results` 应有内容。

### 3.3 Playwright / 浏览器无法访问 `http://localhost:5000`

Docker 容器内 `localhost` ≠ 宿主机。改用宿主机端口：

- 后端：`http://localhost:5000`
- 前端（Nginx 入口）：`http://localhost:80` （前端项目里通过 `/api` 反代到后端）

如部署在云上，请放行 80 端口 + 配置 DNS。

### 3.4 AI 报错：「LLM 环境变量未完整配置」

LLM_API_KEY / LLM_API_URL / LLM_MODEL_NAME 中任一缺失。
检查 `.env` 与 `/api/sys/info` 的 `llm_env_ready` 字段。
修复方法：编辑 `.env` 然后 `docker compose restart backend ai-worker`。

### 3.5 `/admin/analytics` 403

仅 `role=teacher` 可访问。登录用户需为教师。
普通用户访问会得到 HTTP 403。

### 3.6 错题本不更新

- 判题走 judge-worker，若提交记录是考试内（exam_id != -1）且教师已经导入历史数据，
  WrongBookService.on_judge_complete() 在 judge.py 末尾执行，
  若异常不影响主流程但会记日志。
- `docker logs skyoj-judge-worker | grep 错题本` 确认。

### 3.7 Prometheus `/metrics` 端点耗时高

- `http_request_duration_seconds` Histogram 会在高 QPS 场景膨胀历史图。
- 可在 `metrics.py` 中调小 buckets 或在生产环境加 Prometheus federation。

### 3.8 重置数据库

```bash
docker compose down
docker volume rm skyoj_mysql-data
docker compose up -d --build
```

注意：本仓库 `docs/security-debt.md` 中提到：`MYSQL_USER` 与 `MYSQL_PASSWORD`
由 docker-compose 的 `MYSQL_USER: ${MYSQL_PASSWORD}` 环境变量注入，
不需手动 `CREATE USER`。`docker/mysql/init.sql` 仅补充说明，不会覆盖。

---

## 4. 健康检查与监控

### 4.1 后端 `/healthz`

```bash
curl http://localhost:5000/healthz   # 期望 {"status":"ok"}
```

### 4.2 后端 `/metrics`（Prometheus）

```bash
curl http://localhost:5000/metrics | head -30
```

典型指标：

| 指标名                                  | 类型      | 标签                          |
|----------------------------------------|-----------|-------------------------------|
| `http_requests_total`                   | Counter   | method / path / status        |
| `http_request_duration_seconds`         | Histogram | method / path                 |
| `submissions_total`                     | Counter   | problem_type / status         |
| `judge_duration_seconds`                | Histogram | problem_type                  |
| `celery_queue_depth`                    | Gauge     | queue                         |

`celery_queue_depth` 由 backend 的 lifespan 后台任务每 30 秒刷新一次。
首次启动可能返回 `-1`（代表 inspect 尚未连到 worker，正常）。

### 4.3 RabbitMQ 管理 UI

默认启用 `15672` 端口：

```bash
# 默认凭据来自 .env：RABBITMQ_DEFAULT_USER / RABBITMQ_DEFAULT_PASS
docker compose port rabbitmq 15672
```

访问 `http://localhost:15672` 可看队列积压。

---

## 5. 性能与可扩展性

- 题目详情 Redis 缓存：`DETAIL_TTL_SECONDS=600`，TTL 过期自动从 DB 回填；
  任何 `update_problem` / `delete_problem` / `create_problem` 都会失效。
- 排行榜（`exam_service.rank`）走 `exam_cache.py` 内存缓存；
  新提交后会通过 `_invalidate_exam_cache` 异步失效。
- D.17 引入的 Prometheus 指标可作为后续接入 Grafana dashboard 的入口。

---

## 6. 关键文档索引

| 文档                                     | 用途                                              |
|------------------------------------------|---------------------------------------------------|
| `README.md`                              | 项目简介 / 开发速记                                |
| `docs/security-debt.md`                  | 安全债务追踪（含 docker.sock 收口说明）             |
| `docs/analysis/feature-assessment.md`     | 功能清单                                          |
| `docs/analysis/test-report.md`           | 端到端测试结果 + 截图                              |
| `AGENTS.md`                              | 项目协作规范（不可擅改历史等）                     |
| `pyproject.toml`                         | 后端依赖                                          |
| `frontend/package.json`                  | 前端依赖 + 脚本                                   |
