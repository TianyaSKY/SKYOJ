# 已知安全债务

## API 服务挂载 Docker Socket

当前原因：

- ACM、OOP、Kaggle 判题仍由 API 进程直接调用 Docker SDK。

当前缓解措施：

- API 不暴露宿主机 5000 端口。
- 仅通过 Nginx 的 80 端口访问 API。
- 禁止公开注册教师账号。
- 强制配置非默认 `SECRET_KEY`。
- 禁止 MySQL 3306 端口暴露到宿主机。

最终解决方案：

- 里程碑 2 新增独立 Judge Worker。
- 只有 Judge Worker 挂载 Docker Socket。
- API 通过持久化任务表投递判题任务。
- API 服务移除 `/var/run/docker.sock` 挂载。
