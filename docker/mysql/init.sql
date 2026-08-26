CREATE DATABASE IF NOT EXISTS oj_db
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

-- 非 root 应用账号：密码由 docker-compose 的 MYSQL_USER/MYSQL_PASSWORD 环境变量注入。
-- 注意：MySQL 8 早期版本对 CREATE USER 不允许直接使用变量，docker-entrypoint-initdb.d 在
-- 容器首次启动且数据目录为空时执行，因此这里使用拼接 SQL 的方式由 shell 注入。
-- 实际授权脚本由 docker-entrypoint 自动处理（见 docker mysql 镜像默认行为：环境变量
-- MYSQL_USER/MYSQL_PASSWORD 会被 entrypoint 自动创建并赋予对 MYSQL_DATABASE 的全部权限）。
-- 故此处只创建库即可，无需手动 CREATE USER。
