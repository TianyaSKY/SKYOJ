# SKYOJ 实施路线与建议

> 基于 `project-structure.md` 与 `feature-assessment.md` 的结论。
> 工作区在 `e:/PycharmProjects/SKYOJ`，当前分支 `master`，工作区干净。

## 一、整体策略

### 1.1 已完成的"未做之事"

最近 8 次提交集中解决了你清单里的多个高优先级项：

```
b253d14 test(backend): pytest 自动化测试套件
04c4221 perf(backend): ACM 判题从串行改为并发独立容器执行
c5c0080 feat(backend): Redis 缓存考试排行榜结果
0037f7c feat(backend): 基于 Redis 的限流 + 写操作审计中间件
3d9f9df feat(frontend): 提交后 WebSocket 实时显示判题结果
1097cdc feat(backend): WebSocket 实时推送提交判题结果
4abd527 feat(backend): 集成 JPlag 实现代码查重功能
7b4741c feat(frontend): ACM 题目调试入口与结果 Drawer
98e3c09 feat(backend): 新增 ACM 题目单点调试任务链路
ac16d3f feat(backend): 在 AsyncJob 系统注册 debug_submission 任务路由
```

**含义**：后续工作的方向是**进一步深挖教学质量**与**系统韧性**，而不是再补"基础能力"。

### 1.2 仓储根规范遵守

`AGENTS.md` 的关键约束（所有任务都需遵守）：

- 分层：`api / domain / models / repositories / services / clients / tasks / workers / messaging / middleware / utils`
- Pydantic `BaseModel` 校验写请求体 → `@dataclass` 业务参数
- 业务异常类型化 + 全局映射；禁裸 except / 静默吞错 / 暴露堆栈
- Loguru 日志，禁止 `print` / 标准 `logging`
- 注释、文档字符串、内部日志默认中文；标识符英文
- 分支策略：`feat/fix/hotfix/refactor/docs/chore/investigate`，**当前 master 直接提交应切换**
- 不引入未授权的环境变量调整 / secret 删除

---

## 二、建议的实施路线

### 阶段 0：文档与债务清理（1-2 天）

**目标**：把"已实现但文档没改"的项对齐。

| 任务 | 工作量 | 验证方式 |
|---|---|---|
| 更新 `docs/security-debt.md`：标记里程碑 2 已完成（仅 judge-worker 挂 docker.sock），删除"最终解决方案"段 | 0.5h | grep `docker.sock` 在 `docker-compose.yml` 确认 |
| 把 on_event 迁移到 lifespan（`backend/app/main.py:157`） | 1h | `uv run python -m compileall -q backend/app`，启动测试 |
| 修复错误码字段不一致：`utils/request.js` 第 35 行改为 `error.response?.data?.error`，或后端加 `code` 字段 | 1h | 故意登录失效 → 验证 ElMessageBox 弹出 |
| WebSocket 自动重连：`utils/websocket.js:53` 在 onclose 中根据 `closed` 判断 + `setTimeout(connect, RECONNECT_DELAY_MS)` | 1h | 断网测试 |
| 加 `tests/test_error_envelope.py`：断言 401/403/404/429 都返回 `{"error": "..."}` 且不带 stacktrace | 1h | pytest 通过 |
| 提交前建立 `chore/docs-sync-debt` 分支 | — | — |

**风险**：on_event 迁移需要确保测试覆盖 startup 路径。

---

### 阶段 1：教学基础增强（3-4 周）

#### 1.1 题解分享 / 讨论区

**新增模型**（`backend/app/persistence/discussion.py`）：
```python
class SolutionPost(Base):
    __tablename__ = "solution_posts"
    id / problem_id / user_id / title / content_md / code / language
    is_official (bool) / featured (bool) / created_at
    __table_args__ = Index(...)
    # 关系：likes / comments / favorites

class SolutionComment / SolutionLike / SolutionFavorite
```

**关键接口**（`backend/app/api/discussion.py`）：
- `GET /api/problems/{id}/solutions?sort=featured|newest|hot`
- `POST /api/problems/{id}/solutions`（学生，仅当自己有 AC 提交时）
- `POST /api/solutions/{id}/like` / 取消
- `POST /api/solutions/{id}/comments`
- `POST /api/admin/solutions/{id}/feature`

**前端**：
- `ProblemDetailView.vue` 新增"题解"Tab（与 MarkdownContentEditor 复用）
- `SubmissionDetailView.vue` 在 Accepted 时显示"发布题解"按钮

**依赖**：JPlag 查重经验可复用 → 同样需要 dedupe 防刷；评论走分页 + 树形结构。

#### 1.2 题目标签 / 知识点

**新增模型**：
```python
class Tag(Base): id / name / category(knowledge_point|difficulty_topic)
class ProblemTag(Base): problem_id / tag_id  (复合主键)
```

**接口**：
- `GET /api/tags?category=...`
- `POST /api/problems/{id}/tags`（教师）
- `GET /api/problems?tag=dp,graph`

**前端**：ProblemAdminView 用 el-tag 多选 + 远程搜索；ProblemListView 顶部加 tag 过滤 chip。

#### 1.3 学情看板增强

**复用现有**：把 `SubmissionHeatmap.vue` 移到 `TeacherDashboardView.vue` 顶部。

**新增接口**：
- `GET /api/admin/analytics/problem-pass-rate`（按 problem 聚合）
- `GET /api/admin/analytics/error-distribution`（按 status × problem 聚合）

**前端**：新增 `/admin/analytics` 视图（用 ECharts 渲染）。

**风险**：聚合查询可能慢 → 加 Redis 缓存 + 物化视图（MySQL 不支持，先做异步刷新）。

---

### 阶段 2：比赛 / 作业 / 评测扩展（4-6 周）

#### 2.1 比赛模式扩展

**模型改动**（`persistence/exam.py`）：
```python
class Exam(Base):
    # ... 原有字段
    contest_type = Column(Enum("exam", "contest", "homework"), default="exam")
    freeze_time = Column(DateTime, nullable=True)  # 封榜时间
    allow_late = Column(Boolean, default=False)
    late_penalty_percent = Column(Integer, default=0)
```

**服务改动**（`services/exam.py:rank`）：
- 增加 `as_of` 参数；`as_of < freeze_time` 时隐藏冻结期后的提交
- 增加 `users.is_guest` 用于打星显示

**WebSocket 推送**：
- 新增 `/api/exams/{id}/ws` 端点，每次新提交触发排行榜重算 + push

**气球状态**：新增 `Balloon` 表 + 教师后台网格视图（可用 `el-table` + el-tag 状态切换）。

#### 2.2 作业模式

复用 `Exam` 模型的 `contest_type='homework'`，新增：
- `HomeworkSubmission.exam_id` 关联考试
- 提交时 `score *= (1 - late_penalty_percent)` 由 `submission_service.submit` 计算
- 教师可"标记优秀作业" → 在考试结束页展示

#### 2.3 错题本

**模型**：
```python
class WrongBookEntry(Base):
    user_id / problem_id / submission_id / status(Wrong/TLE/RE) / created_at / resolved_at
```

**触发**：在 `judge.judge_submission` 末尾，若 `final_status in {"Wrong Answer", "Time Limit Exceeded", "Runtime Error"}` 且非考试模式 → 自动写入。

**前端**：`/profile` 增加"错题本" Tab + 按 tag 聚合成"复习卷"按钮。

#### 2.4 SPJ / OI 按点给分

**SPJ**：
- `problems.type` 增加 `spj` 枚举值
- 判题流程：跑 ACM → 若 WA 调用 SPJ 容器（镜像内含 checker）
- SPJ 脚本约定：`./spj input.txt user_output.txt expected_output.txt` 返回 0=AC / 1=WA / 2=PE

**OI 按点给分**：
- `submissions.status` 增加 `Partial Score`
- `submission.case_results JSON` 字段保存 `[{"name", "status", "score"}]`
- 前端在 SubmissionDetailView 用进度条展示

---

### 阶段 3：AI 深化与系统韧性（4-8 周）

#### 3.1 AI 答疑 / 代码 review

**接口**（`api/llm.py`）：
```python
class AskLlmBody:
    system: str
    prompt: str
    context_submission_id: Optional[int]  # 新增
    context_problem_id: Optional[int]
    output_format: dict
```

**服务**（`services/llm.py:ask`）：
- 若提供 `context_submission_id`，自动注入提交代码、错误信息、题目描述

**SSE 流式**（`api/llm.py`）：
```python
@router.get("/drafts/{draft_id}/stream")
async def stream_draft(draft_id: int):
    return StreamingResponse(_stream(draft_id), media_type="text/event-stream")
```

前端：`DraftBoxView.vue` 实时刷新 + 用 EventSource 替换轮询。

#### 3.2 编译缓存 / Warm Pool

**编译缓存**（轻量）：
- `services/acm.py:_ACM_LANG_CONFIGS` 编译产物按 `(lang, code_hash)` 存 `uploads/cache/{lang}/{hash}.bin`
- Judge worker 启动时预热常用模板

**Warm Pool**（重，需谨慎）：
- 在 judge worker 启动时预创建 N 个容器（每种语言）
- 提交时从池中取一个，用完归还
- 风险：Docker SDK API 不支持容器复用，需通过"运行后保留容器 + exec_run"实现

#### 3.3 可观测性

**Prometheus**：
- 后端加 `prometheus-fastapi-instrumentator` 中间件 → `/metrics`
- Celery 走 RabbitMQ Prometheus exporter
- 自定义指标：`skyoj_judge_queue_depth`, `skyoj_submission_total{status}`

**Grafana** 看板：
- 队列深度 / Worker 状态 / API 延迟 / 判题失败率

**告警**：
- judge queue depth > 100 → Slack/邮件
- judge worker 5 分钟无心跳 → Slack

---

### 阶段 4：规模化与跨端（远期）

| 方向 | 工作量 | 前置条件 |
|---|---|---|
| 题目推荐系统 | 4 周 | 知识点标签 + 用户错题历史 |
| 学生互评 | 3 周 | 作业模式完成 |
| 多语言（Go/Rust/JS） | 1 周/语言 | runner 镜像加编译器；acm.py 加语言配置 |
| E2E 测试 + 前端测试 | 3 周 | 阶段 1 完成稳定后 |
| PWA / 移动端优化 | 4 周 | 响应式基础已有 |
| 镜像构建推送 workflow | 1 天 | 注册 Docker Hub / GHCR |

---

## 三、风险与建议

### 3.1 架构层面

| 风险 | 影响 | 缓解 |
|---|---|---|
| 单分支 `master` 直接提交 | 多人协作冲突 | 立即启用 `feat/.../fix/...` 分支策略 |
| API 进程与 Worker 共享 `app.core.config` | LLM/Redis 等 env 在 Worker 也必须存在 | 已通过 `docker-compose.yml` 解决 |
| WebSocket 仅 Redis PubSub | 单点 / 不可水平扩展 | 已支持多 worker 连接同一 Redis，可后续加 Redis Sentinel |
| 测试用 SQLite | 部分 MySQL 特性（JSON 列、枚举）可能不一致 | pytest 用 SQLite 是约定，需在 conftest 显式跳过这些 case |

### 3.2 判题与安全

| 风险 | 影响 | 缓解 |
|---|---|---|
| Docker socket 暴露给 worker | 容器逃逸 | `network_mode=none` + Cgroups；JPlag 容器独立 |
| 编译缓存未做 | 编译耗时长 | 阶段 3.2 实施 |
| Warm Pool 复杂度 | 实现风险高 | 优先编译缓存而非容器复用 |
| 代码注入 | 学生代码在容器内 | 沙箱已隔离；可加静态扫描（detect-secrets 类工具） |

### 3.3 测试与质量

| 风险 | 影响 | 缓解 |
|---|---|---|
| 无前端组件测试 | 重构容易回归 | 加 Vitest + Vue Test Utils |
| 无 E2E | 主链路（登录→提交→判题→查重）回归靠人工 | 阶段 4 加 Playwright |
| 判题结果回归测试 | 容器化测试复杂 | 用 docker-in-docker 或 mock SandboxRunner |
| CI 不跑前端测试 | 无 | 加 `frontend-test` job |

### 3.4 文档与运维

| 风险 | 影响 | 缓解 |
|---|---|---|
| security-debt.md 过期 | 新人误解 | 阶段 0 修 |
| README 与代码不同步（"WebSocket 实时推送""Redis 限流"等已实现但 README 笼统） | 用户/贡献者困惑 | 在 README 加 "Recent Changes" 段 |
| 无 OpenAPI 导出 | 前端类型对不齐 | FastAPI 已自带 `/docs`，可加 `spectree` 生成前端 zod schema |
| 无运维手册 | 出问题只能查源码 | 加 `docs/operations.md`（常见故障 / 队列积压 / 容器清理） |

### 3.5 关键非技术风险

| 风险 | 建议 |
|---|---|
| LLM API 供应商变更 / 价格波动 | 把 LLM 客户端封到 `clients/llm_client.py` 已有抽象，扩展时只动这一个文件 |
| MySQL → PostgreSQL 迁移 | 当前 ORM 是 SQLAlchemy，迁移成本可控；但 JSON 字段语法差异需注意 |
| 沙箱镜像体积 | runner 镜像装 4 语言后约 1GB，可分拆为 `runner-c / runner-py / runner-java`，按 problem.language 选镜像 |

---

## 四、立刻可执行的 5 件事

如果你只能做 5 件事，按 ROI 排序：

1. **修 `utils/request.js` 错误码**（1h，修复登录失效提示永久不弹）
2. **修 `docs/security-debt.md`**（30min，消除新人误解）
3. **FastAPI `lifespan` 迁移**（1h，消除 DeprecationWarning）
4. **WebSocket 自动重连**（2h，提升断网体验）
5. **题目 Markdown Redis 缓存**（半天，SQL 压力下降）

---

## 五、最终交付物清单

本目标在 `docs/analysis/` 下产出 3 份文档：

```
docs/analysis/
├── project-structure.md      # 仓库结构 + 分层 + 模型 + 工程实践
├── feature-assessment.md     # 16+ 优化方向逐项评估（状态表 + 重新排序）
└── roadmap.md                # 实施路线 + 风险 + 建议（本文档）
```

`docs/security-debt.md` 仍保持原状，待阶段 0 处理。
