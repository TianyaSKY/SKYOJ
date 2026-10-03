# 架构与数据库初始化

HTTP 写请求由 `api/schemas/` 中的 Pydantic 模型校验，并转换成业务 dataclass。Service 返回固定类型的业务结果，API 声明响应模型；文件下载、204 空响应和 SSE 显式使用 `response_model=None`。

平台统计在 Repository 中使用 SQL 聚合，只将统计行传给 Service。查重查询在 Repository 内完成，Service 不再直接访问 Session 或 ORM 查询。同步 LLM 的仓储由 `api/deps.py` 注入；Worker 在任务入口装配仓储与运行器。

动态系统配置、LLM JSON 和任务载荷使用明确的递归 `JsonValue` 类型。固定统计使用专用 dataclass；动态业务结果使用 `JsonObjectResult` 包装，在 HTTP 或消息边界取出 `payload`。缓存、数据库 JSON 列和外部协议仍允许字典。

## 后端目录与依赖

业务代码按 `api / services / persistence / clients` 四类职责组织。业务参数、结果与 Service 放在同一文件；SQLAlchemy 模型、Repository 和数据库映射按业务上下文放在同一持久化文件。

```text
backend/app/
├── api/                   # HTTP、鉴权入口、Pydantic schemas 与依赖装配
├── services/              # Params / Result dataclass 与业务编排
│   ├── problem.py
│   ├── exam.py
│   ├── submission.py
│   ├── user.py
│   ├── dataset.py
│   └── ...
├── persistence/
│   ├── database.py        # Base、Session 工厂、请求会话
│   ├── unit_of_work.py    # 显式注入 Service 的事务封装
│   ├── problem.py
│   ├── community.py       # 题解、评论、点赞、收藏、标签
│   ├── exam.py
│   ├── submission.py      # 提交、调试运行、查重报告
│   ├── user.py            # 用户、错题本、搜索历史
│   ├── dataset.py
│   ├── jobs.py            # 异步任务与 AI 草稿
│   └── system.py          # 系统字典与审计日志
├── clients/               # LLM、文件存储、JPlag 等外部调用
├── judging/               # ACM、OOP、Kaggle、sandbox 与测试数据生成
├── core/                  # config、errors、time、JSON、Token 与密码辅助函数
├── messaging/
├── tasks/
├── workers/
└── middleware/
```

旧的 `domain/`、`models/`、`repositories/`、全局 `mappers.py` 和 `*_service.py` 兼容入口均已删除。新增代码直接使用以上路径；HTTP 协议和数据库表结构保持原有约定，无需新增数据库迁移。

Repository 返回明确的 dataclass 快照，包含必要的关联信息，不把 ORM 对象或 Session 传给 Service。快照类型由 persistence 定义，公开展示结果由相应 Service 转换。Client 定义自己的存储/外部协议结果，由 Service 转换为业务结果；persistence 和 clients 均不得引用 services 或 api。快照脱离 Session 后仍可读取；修改快照不会自动写入数据库，必须调用仓储的更新方法。数据集快照为不可变类型；题目、考试和社区的编辑流程使用可修改快照并显式保存。提交判题 JSON 与查重匹配块在快照中复制，避免共享 ORM 的可变 JSON 值。

`api/deps.py` 为 Service 显式注入所需仓储与 Client，包含题目标签查询所需的社区仓储。社区、错题本服务不再接收 Session；异步任务服务不再提供 `from_session` 工厂，API 与 Worker 使用 `AsyncJobService(AsyncJobRepository(db), uow=uow)` 装配。判题模式由 Worker 传入会话，不再隐式创建额外会话。

`persistence/__init__.py` 统一注册全部 ORM 表与字符串关联。API、Worker 与种子脚本均使用同一注册入口；持久化层在自己的模块内构造快照，不再反向引用 Service。

## 事务

Repository 仅执行数据访问、`flush()` 和必要的 `refresh()`，不调用 `commit()` 或 `rollback()`。Service 通过构造参数显式接收 `UnitOfWork`，Repository 不持有 UoW；跨仓储写入使用 `uow.transaction()`，成功统一提交，异常立即回滚。

请求使用同一个 Session，失败由 `persistence/database.py` 回滚并关闭；成功写入继续由现有 Service/UoW 显式提交。没有改成“请求结束统一 commit”，因为任务发布必须发生在记录提交之后。社区的点赞、收藏、评论和计数更新处于同一业务事务；错题本复习标记先校验归属，再更新。

任务创建记录必须提交后再发布到 RabbitMQ；重试和租约恢复也先持久化状态再发布消息。提交、调试、草稿、数据集的业务记录先 flush，再在同一 Session/UoW 中创建任务，一次提交两者；任务创建或提交失败时共同回滚。`async_jobs` 同时充当持久化投递日志：RabbitMQ 发布失败时保留 pending 任务并记录异常，API 仍接受请求，恢复 Worker 会补发任务。数据集的临时文件只有在数据库事务失败时清理，已提交的任务保留文件用于后续落盘。投递允许重复，Worker 使用原子领取吸收重复消息；恢复 Worker 必须持续运行。

判题结果与错题本在同一事务保存；错题本写入失败时回滚结果并由任务骨架重试。自动查重幂等键包含题目与提交 ID，每次新 Accepted 提交可以触发扫描，同一提交重试不重复建任务；教师手动扫描每次创建独立任务。Redis 通知、缓存和指标保留辅助降级语义，失败记录日志。

Worker 捕获执行异常后先回滚失败事务，再写入任务失败状态，避免 SQLAlchemy 会话处于失败状态而无法记录错误。

## 初始化数据库

`main.py` 仅装配应用与生命周期，路由、异常响应、指标分别位于 `api/router.py`、`api/errors.py`、`middleware/metrics.py`；数据库初始化位于 `persistence/bootstrap.py`。鉴权入口在 `api/auth_context.py`，JWT 编解码在 `core/auth_tokens.py`。题目与考试缓存键留在所属 Service，共享 `clients/redis_client.py` 的 JSON/发布操作；旧 `utils/` 已删除。

配置 `DATABASE_URL`、`SECRET_KEY` 后启动 API。启动流程检查连接，通过 SQLAlchemy `Base.metadata.create_all()` 创建缺失的表，然后初始化系统默认数据；初始化失败将拒绝启动。

Docker Compose 的 Worker 和恢复进程等待 API 健康检查通过后启动。本地启动时先等待 API 初始化完成，再启动 Worker。

建表操作可重复执行，保留已有表和数据，不自动新增、删除或修改已有表的字段、索引及约束。已有数据库的结构变更需要备份后手动执行 SQL；项目不再维护数据库版本及迁移脚本。

## 验证与持续检查

```bash
uv run python -m pytest -q backend/tests
npm --prefix frontend run test:unit
npm --prefix frontend run build
```

`test_architecture_contracts.py` 检查新目录下的仓储事务调用、Service 的数据库泄漏、公共结果类型、HTTP 响应模型、旧包清理和完整表注册。`test_persistence_boundaries.py` 验证快照及其关联中没有 ORM、脱离 Session 后仍可使用、社区计数与关联写入共同回滚、标签审批更新、错题本访问控制、重复查重更新及请求失败回滚。任务 JSON 解析和缓存序列化属于明确的字典边界。

前端 `auth/problem/exam` Zod 校验对应后端字段长度、枚举和范围；时间先后关系同时由前端改善体验、后端 Service 权威检查。

独立的浏览器校验回归可针对预览服务运行（API 被可控响应替代）：

```bash
npm --prefix frontend run preview -- --port 4173
# 另一个终端
cd frontend
E2E_BASE_URL=http://127.0.0.1:4173 npm run test:e2e -- e2e/validation.spec.js --project=chromium --project=chromium-mobile
```

CI 为完整 `frontend/e2e` 套件使用 `backend/scripts/seed_e2e.py` 创建表并填充专用临时 `skyoj-e2e.sqlite`。脚本拒绝其他数据库和已有用户的数据，不能对业务库运行。Playwright 管理 API（5015）与预览服务（4173），等待健康检查后才开始测试；认证 fixture 使用实际登录接口签发的 token。预览代理通过 `E2E_API_URL` 指向独立 API。考试模式的系统信息按浏览器页面隔离，避免并行修改全局配置互相干扰。

本地复现完整 CI 浏览器套件时，在仓库根目录设置隔离环境（使用全新的临时目录）：

```bash
E2E_TMP=$(mktemp -d)
export DATABASE_URL="sqlite:///$E2E_TMP/skyoj-e2e.sqlite"
export SECRET_KEY=local-e2e-secret-key
export CELERY_BROKER_URL=memory:// REDIS_URL=''
export UPLOAD_FOLDER="$E2E_TMP/uploads"
export E2E_BASE_URL=http://127.0.0.1:4173 E2E_API_URL=http://127.0.0.1:5015
uv sync --frozen
uv run python backend/scripts/seed_e2e.py
cd frontend
npm ci
npx playwright install
npm run build
CI=true npm run test:e2e
```

失败会真实导致 CI 失败，并上传报告、截图和 trace。此环境覆盖页面与真实 API、数据库交互；Celery 使用内存 broker，未启动判题执行器或外部 LLM，不代表 Docker 判题全链路验证。部分历史用例的断言仍较弱，需要逐步增强，不能把通过数量等同于完整业务覆盖。

测试夹具使用外层事务与独立保存点，使业务 commit/rollback 不会破坏测试种子或泄漏到下一用例；专门的事务回归使用独立数据库验证真实提交和回滚。

## 本次收拢验证（2026-10-03）

后端 172 项 pytest、前端 31 项单元测试、前端构建、源码编译与 Compose 配置检查通过。与收拢前提交 `7567447` 对比，20 个 ORM 类定义和完整 OpenAPI（65 个 HTTP 路径及全部 schemas）一致。API、全部任务入口、恢复 Worker 与 Celery 注册装配通过；上述验证为收拢完成时的记录；移除迁移机制后的启动回归覆盖空库建表、重复启动保留数据和建表失败拒绝启动。未执行真实 MySQL、RabbitMQ、Docker 判题、外部 LLM/JPlag 或完整浏览器端到端链路。

## 第二阶段收拢（2026-10-03）

本轮保留启动建表及现有数据库结构，未引入 Alembic。新增架构约束覆盖 persistence/clients 反向依赖、Repository 不持有 UoW、旧 utils 与判题兼容模块清理。`test_async_business_transactions.py` 使用独立 SQLite 会话验证四种异步业务在任务创建失败时共同回滚、发布失败时共同持久化并可恢复，以及判题/错题本原子保存和自动/手动查重重复触发规则。

验证结果：186 项后端 pytest 通过；源码编译与差异空白检查通过；与本轮修改前 `4c548c2` 对比，完整 OpenAPI、20 张表及索引的 SQLite DDL 一致，API、全部任务入口与恢复 Worker 可装配。事务测试使用独立 SQLite 会话，RabbitMQ 发布失败通过注入异常验证；未运行真实 MySQL、RabbitMQ、Docker 判题或外部 LLM/JPlag。
