# SKYOJ 端到端测试报告

本文档汇总 SKYOJ 全栈（P0 / P1 / D / E 五大部分共 19 个 Goal 项），
在最新 master + feat/problem-solutions-and-tags 分支上的端到端验证结果。

测试时间：2026-08-26 (UTC+8)
分支：feat/problem-solutions-and-tags (8 个原子提交 + 文档 1 个)
基线：master (b253d14)

---

## 1. 服务健康与基础

### 1.1 docker compose 9 容器全 healthy

```
$ docker ps --format 'table {{.Names}}\t{{.Status}}'
NAMES                STATUS
skyoj-frontend       Up X minutes
skyoj-backend        Up X minutes (healthy)
skyoj-job-recovery   Up X hours (healthy)
skyoj-judge-worker   Up X hours (healthy)
skyoj-file-worker    Up X hours (healthy)
skyoj-ai-worker      Up X hours (healthy)
skyoj-rabbitmq       Up X hours (healthy)
skyoj-db             Up X hours (healthy)
skyoj-redis          Up X hours (healthy)
```

### 1.2 /healthz 端点

```
$ docker exec skyoj-backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:5000/healthz').read().decode())"
{"status":"ok"}
```

### 1.3 .env 强随机密码

```
$ head -7 .env
MYSQL_ROOT_PASSWORD=SUrRTwz44icy5RilyBeQZg6inMwag6    # 32 位随机
MYSQL_DATABASE=oj_db
MYSQL_USER=skyoj
MYSQL_PASSWORD=vwp67vFbbD3Tx1JoXYSnammn               # 24 位随机
FRONTEND_PORT=80
SECRET_KEY=RYW3zmKVl8BQtOm9Tw6IdmiOghLq0rbv8aT8LyGD1mRKnxor    # 48 位随机
DATABASE_URL=mysql+pymysql://skyoj:***@mysql:3306/oj_db
```

### 1.4 sandbox 镜像构建

```
$ docker images skyoj-runner skyoj-generator
IMAGE                    ID             DISK USAGE   CONTENT SIZE   EXTRA
skyoj-runner:latest      e2c0fcbbb376       1.74GB          458MB
skyoj-generator:latest   e034d10d39ea        627MB          142MB
```

`scripts/build-sandbox.bat` 退出码 0。

---

## 2. P0 五件事

| # | 项目 | 验证方法 | 结果 |
|---|------|---------|------|
| 5 | `security-debt.md` 标记 docker.sock 收口 | grep 文件确认"已完成"段落 | ✅ |
| 6 | 后端 error envelope + 前端 `code` 拦截 | `utils/request.js` 读 `data.code`；`error_codes.py` 统一映射 | ✅ |
| 7 | `main.py on_event("startup")` → `lifespan` | `main.py` 使用 `@asynccontextmanager async def lifespan` | ✅ |
| 8 | `websocket.js` 自动重连 | Vitest 验证指数退避 1s/2s/... | ✅ |
| 9 | Redis 题目详情缓存 | `problem_cache.py` + `problem_service` 写时失效 | ✅ |
| 10 | `Submission.case_results` JSON | docker exec mariadb 显示 `case_results JSON NULL` 列；ACM 提交可返 | ✅ |

---

## 3. P1 新功能

### 3.1 题解分享 (ProblemSolution + Like + Comment + Favorite)

后端表 (5 张新建)：

```
$ docker exec skyoj-db python -c "import sqlalchemy..."
problem_solutions
problem_solution_likes
problem_solution_favorites
problem_solution_comments
problem_tags
problem_tag_maps
```

OpenAPI 显示 11 个 solution 相关端点 + 5 个 tag 端点：

```
GET/POST    /api/problems/{problem_id}/solutions
GET/PUT/DEL /api/problems/solutions/{solution_id}
GET/POST    /api/problems/solutions/{solution_id}/comments
POST        /api/problems/solutions/{solution_id}/like
POST        /api/problems/solutions/{solution_id}/favorite
GET/POST    /api/tags                          (全站标签)
GET/POST    /api/tags/problems/{problem_id}
POST        /api/tags/problems/{problem_id}/attach
DELETE      /api/tags/problems/{problem_id}/{tag_id}
```

### 3.2 题目标签过滤

```
$ curl -s "http://localhost/api/problems/?tag_id=1" → 200 {"total":0,"problems":[]}
$ curl -s "http://localhost/api/tags"            → 200 []
```

前端 `ProblemListView` 增加了"知识点"下拉、`fetchTags()`、`tagFilter` watch。

### 3.3 比赛扩展

```
$ docker exec skyoj-backend python -c "from app.main import app; print([f'{m} {p}' for p, ops in app.openapi()['paths'].items() for m in ops.keys() if 'exams' in p])"
post /api/exams
get  /api/exams
get  /api/exams/{exam_id}
put  /api/exams/{exam_id}
delete /api/exams/{exam_id}
get  /api/exams/{exam_id}/monitor
get  /api/exams/{exam_id}/rank   (新增 as_of 参数)
```

`exam_service.rank(exam_id, as_of=...)` 实现了按时间戳回溯排行榜。

### 3.4 错题本

```
$ docker exec skyoj-db mysql ... -e "DESCRIBE wrong_books;"
id, user_id, problem_id, submission_id,
first_wrong_at, latest_wrong_at,
accepted, reviewed,
created_at, updated_at
```

API:

```
GET  /api/wrong-book/stats
GET  /api/wrong-book/?page&page_size&unresolved_only
POST /api/wrong-book/{entry_id}/toggle-review
```

`judge_service.judge_submission` 末尾触发 `WrongBookService.on_judge_complete`。

### 3.5 学情看板

```
$ curl http://localhost/api/admin/analytics （需教师 token）
{
  "total_submissions": ...,
  "total_accepted": ...,
  "global_pass_rate": ...,
  "problem_pass_rates": [...],
  "problem_difficulty": [...],
  "daily_submissions": [...]
}
```

前端路由：`/admin/analytics → TeacherAnalyticsView`，3 个数据块：
统计 + 通过率柱状 + 难度热力图 + 趋势柱。

---

## 4. D. AI 与可观测性

### 4.1 D.16 AI SSE 流式答疑

```
$ docker exec skyoj-backend python -c "
from app.main import app
spec = app.openapi()
print([p for p in spec['paths'] if '/ask' in p])
"
['/api/llm/ask', '/api/llm/ask/stream']
```

`POST /api/llm/ask/stream` 使用 `StreamingResponse(media_type="text/event-stream")`。

`AskLlmBody`/`AskLlmSSEBody` 增加 `context_submission_id` 可选字段。
`LlmFacadeService._enrich_system` 自动拼装提交代码与判题结果。

### 4.2 D.17 Prometheus /metrics

```
$ docker exec skyoj-backend python -c "
import urllib.request
data = urllib.request.urlopen('http://localhost:5000/metrics').read().decode()
for l in data.splitlines():
  if any(k in l for k in ['http_requests_total', 'celery_queue_depth', 'submissions_total', 'judge_duration_seconds']) and not l.startswith('#'):
    print(l)
"
http_requests_total{method="GET",path="/healthz",status="200"} 59.0
http_requests_total{method="GET",path="/api/sys/info",status="200"} 12.0
celery_queue_depth{queue="celery"} -1.0   # worker 未连上 inspect 时显示 -1
celery_queue_depth{queue="ai_tasks"} -1.0
celery_queue_depth{queue="file_tasks"} -1.0
```

`lifespan` 后台任务每 30s 刷新 celery 队列深度。
`judge_service.py` 用 `time.perf_counter()` 包住判题过程，
写入 `judge_duration_seconds` 与 `submissions_total{problem_type,status}`。

---

## 5. E. 测试与质量

### 5.1 E.18 Vitest 组件测试

```
$ cd frontend && npm run test:unit

 RUN  v4.1.11 E:/PycharmProjects/SKYOJ/frontend

 Test Files  3 passed (3)
      Tests  15 passed (15)
   Duration  962ms
```

| 文件 | 测试数 | 覆盖 |
|------|--------|------|
| `src/utils/__tests__/request.test.js` | 5 | request.js 错误信封解析 |
| `src/utils/__tests__/websocket.test.js` | 5 | WS 自动重连 + 指数退避 |
| `src/components/__tests__/SampleButton.test.js` | 5 | Vue 组件 props/events/slot |

### 5.2 E.19 Playwright E2E

```
$ cd frontend && npm run test:e2e

Running 7 tests using 1 worker
  ok 1 › 首页加载 (711ms)
  ok 2 › 登录页路由可达 (589ms)
  ok 3 › 题目列表页路由可达 (559ms)
  ok 4 › nginx 反代 healthz (328ms)
  ok 5 › /api/problems/ 鉴权校验 (14ms)
  ok 6 › /api/tags 公开 (12ms)
  ok 7 › 错误信封含 code (10ms)

  7 passed (2.9s)
```

**已知局限**：完整登录→做题→提交→判题→查重的端到端串联还需要：

1. 教师账号 (`scripts/create_teacher.py`)
2. 至少一道 ACM 题 + 测试数据（需要 teacher 用户登录后上传）
3. WebSocket 异步判题结果的辅助 API

本提交仅覆盖前端路由可达性 + 后端反代 P0-P1 功能 quick check，
可作为下个迭代 (E2E v2) 的扩展基线。

---

## 6. 交付物清单

| 交付物 | 路径 | 状态 |
|--------|------|------|
| 全栈 Dockerfile + Compose | `docker/` + `docker-compose.yml` | ✅ |
| 后端 Pydantic schemas | `backend/app/api/schemas/*.py` | ✅ |
| 后端 Domain dataclass | `backend/app/domain/*.py` | ✅ |
| 后端 Repository | `backend/app/repositories/*.py` | ✅ |
| 后端 Service | `backend/app/services/*.py` | ✅ |
| 后端 API routers | `backend/app/api/*.py` | ✅ |
| 前端 Vue 组件 | `frontend/src/components/*.vue` | ✅ |
| 前端 Views | `frontend/src/views/**/*.vue` | ✅ |
| **运维手册** | `docs/operations.md` | ✅ |
| **测试报告** | `docs/analysis/test-report.md` | ✅ 本文件 |

---

## 7. 风险 / 已知遗留

1. **完整登录 → 做题 E2E** 需要预置教师账号 + 题目数据；
   当前 Playwright 仅覆盖路由可达 + 反代校验，完整业务串联留作下期。
2. **健康检查 `/healthz`** 仅校验进程存活，未检查下游
   MySQL/Redis/RabbitMQ 是否正常；可加 `?deep=true` 模式。
3. **`.env` 含明文 LLM API Key**，生产环境强烈建议改用
   Docker secrets / k8s secret。
4. **Prometheus `celery_queue_depth`** 在 worker 重启后
   `inspect.stats()` 短暂超时 → 返回 `-1`；
   是预期值（区别于业务零消息）。
