# 架构与数据库迁移

HTTP 写请求由 `api/schemas/` 中的 Pydantic 模型校验，并转换成领域 dataclass。Service 返回固定类型的业务结果，API 声明响应模型；文件下载、204 空响应和 SSE 显式使用 `response_model=None`。

平台统计在 Repository 中使用 SQL 聚合，只将统计行传给 Service。查重查询在 Repository 内完成，Service 不再直接访问 Session 或 ORM 查询。同步 LLM 的仓储由 `api/deps.py` 注入；Worker 在任务入口装配仓储与运行器。

动态系统配置、LLM JSON 和任务载荷使用明确的递归 `JsonValue` 类型。固定统计使用专用 dataclass；动态业务结果使用 `JsonObjectResult` 包装，在 HTTP 或消息边界取出 `payload`。缓存、数据库 JSON 列和外部协议仍允许字典。

## 后端目录收拢（迁移中）

目标保留 `api / services / persistence / clients` 四类角色。新增或迁移的模块不再新增 `domain/*.py`、`models/*.py`、`repositories/*_repository.py` 或全局 mapper；按业务上下文收拢，不改 HTTP 协议或表结构。

首个样板为数据集：

- `services/dataset.py`：业务参数、结果 dataclass 与 `DatasetService`。
- `persistence/dataset.py`：`Dataset` ORM、`DatasetRepository` 与数据库映射。
- `api/dataset.py`、`api/deps.py` 和 File Worker 使用新路径。

数据集仓储的 `get_by_id/create/mark_ready/mark_failed` 返回不可变 `DatasetRecord` 快照；`list_all` 返回 `DatasetListItem` 列表。Service 不持有 ORM，也不调用 ORM mapper。更新状态后必须使用仓储返回的新快照；直接修改旧快照不会写入数据库。`delete` 接收快照并按其 ID 删除记录。事务继续由现有 Service/UoW 管理。

原有 `domain/dataset.py`、`models/dataset.py`、`repositories/dataset_repository.py`、`services/dataset_service.py` 和全局数据集 mapper 入口只保留兼容导出，类型和 ORM 表注册不会重复。兼容层仅保障旧导入路径，仓储结果已改为上述快照契约。

其余业务模块尚未迁移。后续逐个收拢 user、problem、submission，再处理 exam 与 community；全部调用方迁移并验证后删除兼容层。数据库连接模块、公共错误和事务方案在后续阶段统一处理。

## 事务

Repository 仅执行数据访问和 `flush()`，不调用 `commit()` 或 `rollback()`。Service 通过仓储的 `unit_of_work` 控制业务事务；跨仓储写入使用 `unit_of_work.transaction()`，成功统一提交，异常立即回滚。

任务创建记录必须提交后再发布到 RabbitMQ；重试和租约恢复也先持久化状态再发布消息。当前创建提交、草稿、数据集仍保留“先提交业务记录，再创建并发布任务”的原有语义。消息投递失败会撤销任务记录，但业务记录可能已存在；这并非完整的业务记录与消息原子提交，后续若需要这一保证，应引入持久 Outbox。

Worker 捕获执行异常后先回滚失败事务，再写入任务失败状态，避免 SQLAlchemy 会话处于失败状态而无法记录错误。

## 升级数据库

配置 `DATABASE_URL`、`SECRET_KEY` 后，从仓库根目录执行：

```bash
uv sync --frozen
uv run alembic -c backend/alembic.ini upgrade head
```

从 `backend/` 执行时使用 `-c alembic.ini`。本地 API 和 Worker 均须在迁移成功后启动；应用启动仅检查连接并初始化系统默认数据，不执行 DDL，初始化失败将拒绝启动。

Docker Compose 包含独立 `migrate` 服务，API、Worker 和恢复进程通过 `service_completed_successfully` 等待迁移成功。

初始迁移 `0001` 冻结了引入迁移时的表结构：空库创建表，旧库保留已有表和数据，补充此前启动脚本维护的 `datasets` 文件任务字段、`submissions.case_results`、`exams.contest_type/freeze_minutes` 及索引。迁移按版本执行；DDL 错误不会被忽略。

既有库应先备份，并在备份副本验证升级。初始迁移只接管受支持的旧结构，不会自动修复任意字段类型或约束漂移。MySQL DDL 可能自动提交，迁移中断后应排查原因并重试，不能依赖事务恢复已执行的 DDL。初始版本禁止自动 downgrade，以免删除接管的历史表；回退应使用已验证的备份。后续结构变更须新增迁移文件，不修改已发布的版本。

## 验证与持续检查

```bash
uv run python -m pytest -q backend/tests
npm --prefix frontend run test:unit
npm --prefix frontend run build
```

`test_architecture_contracts.py` 检查仓储事务调用、已整改服务的数据库泄漏、Service 公共字典结果及 HTTP 响应模型。任务 JSON 解析被明确视为序列化边界。

前端 `auth/problem/exam` Zod 校验对应后端字段长度、枚举和范围；时间先后关系同时由前端改善体验、后端 Service 权威检查。

独立的浏览器校验回归可针对预览服务运行（API 被可控响应替代）：

```bash
npm --prefix frontend run preview -- --port 4173
# 另一个终端
cd frontend
E2E_BASE_URL=http://127.0.0.1:4173 npm run test:e2e -- e2e/validation.spec.js --project=chromium --project=chromium-mobile
```

CI 为完整 `frontend/e2e` 套件执行 Alembic 迁移，再用 `backend/scripts/seed_e2e.py` 填充专用临时 `skyoj-e2e.sqlite`。脚本拒绝其他数据库和已有用户的数据，不能对业务库运行。Playwright 管理 API（5015）与预览服务（4173），等待健康检查后才开始测试；认证 fixture 使用实际登录接口签发的 token。预览代理通过 `E2E_API_URL` 指向独立 API。考试模式的系统信息按浏览器页面隔离，避免并行修改全局配置互相干扰。

本地复现完整 CI 浏览器套件时，在仓库根目录设置隔离环境（使用全新的临时目录）：

```bash
E2E_TMP=$(mktemp -d)
export DATABASE_URL="sqlite:///$E2E_TMP/skyoj-e2e.sqlite"
export SECRET_KEY=local-e2e-secret-key
export CELERY_BROKER_URL=memory:// REDIS_URL=''
export UPLOAD_FOLDER="$E2E_TMP/uploads"
export E2E_BASE_URL=http://127.0.0.1:4173 E2E_API_URL=http://127.0.0.1:5015
uv sync --frozen
uv run alembic -c backend/alembic.ini upgrade head
uv run python backend/scripts/seed_e2e.py
cd frontend
npm ci
npx playwright install
npm run build
CI=true npm run test:e2e
```

失败会真实导致 CI 失败，并上传报告、截图和 trace。此环境覆盖页面与真实 API、数据库交互；Celery 使用内存 broker，未启动判题执行器或外部 LLM，不代表 Docker 判题全链路验证。部分历史用例的断言仍较弱，需要逐步增强，不能把通过数量等同于完整业务覆盖。

判题执行器和社区/错题本仍保留部分历史 Session 装配方式；本次分层检查针对已整改服务，不代表整个仓库已完成所有架构迁移。
