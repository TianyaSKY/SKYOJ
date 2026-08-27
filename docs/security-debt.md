# 已知安全债务

## Judge Worker 挂载 Docker Socket

**状态**：✅ 已闭环（里程碑 2，commit 见 `git log --grep='judge-worker'` / `fix(backend): break judge import cycle`）

当前架构：

- `docker-compose.yml` 中只有 `judge-worker` 服务挂载 `/var/run/docker.sock`（仅 judge 容器能启动判题沙箱）。
- API（`backend`）容器**不挂载** docker socket、不调用 `docker.from_env()`。
- 判题请求经 `submission_service.submit` → `AsyncJobService.enqueue_judge_submission` 写入 `async_jobs` 表 → 由 RabbitMQ 投递到 judge worker 消费。
- 缓解措施（仍然有效）：
  - API 不暴露宿主机 5000 端口（仅容器内 `expose`，由 Nginx 反代）。
  - 禁止公开注册教师账号（`scripts/create_teacher.py` CLI 创建）。
  - 强制配置非默认 `SECRET_KEY`（`.env.example` 拒绝占位符）。
  - MySQL 3306 仅 `127.0.0.1` 暴露到宿主机。
  - 限流：登录 5/60s、注册 3/60s、提交 10/60s（Redis fixed-window）。
  - 写操作审计：`AuditMiddleware` 自动记录 POST/PUT/DELETE/PATCH 的 method/path/IP/UA/载荷摘要到 `audit_log` 表。

- 沙箱使用 `network_mode=none`、`pids_limit`、`cap_drop=ALL` 和 `no-new-privileges`。

回归检测（CI/本地）：

- `docker compose config` 检查 `services.backend.volumes` 不含 `/var/run/docker.sock`。
- `docker compose config` 检查 `services.judge-worker.volumes` 含 `/var/run/docker.sock`。
- 定期 `grep -R "docker.from_env" backend/app/` 确认调用点仅在 `services/sandbox_runner.py`，且该文件只在 judge 进程的 worker 上下文中被 import。

后续可选加固：

- 使用 rootless Docker 或独立 Judge 主机，进一步缩小 docker.sock 的爆炸半径。
