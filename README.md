# SKYOJ

SKYOJ 是一个基于 Vue3 + Flask + MySQL + Docker 构建的在线评测系统（Online Judge）。它不仅支持传统的 ACM 判题模式，还针对教学场景设计了面向对象（OOP）测试模式和数据科学竞赛（Kaggle）模式。

## 🌟 核心特性

- **多模式判题**：
  - **ACM 模式**：标准输入输出比对。
  - **OOP 模式**：基于单元测试（unittest/pytest）的代码片段评测。
  - **Kaggle 模式**：基于 CSV 文件的结果评分（支持 RMSE, F1-Score 等指标）。
- **容器化隔离**：所有用户提交的代码均在独立的 Docker 容器中运行，确保系统安全。
- **异步处理**：采用异步调度机制，确保在高并发提交下前端依然流畅。
- **全栈部署**：提供完整的 Docker Compose 配置，实现一键本地或服务器部署。

## 📂 项目结构

```text
SKYOJ/
├── backend/            # Flask 后端应用
│   ├── app/            # 核心业务逻辑 (API, Models, Services)
│   ├── uploads/        # 题目数据与提交文件存储
│   └── Dockerfile      # 后端镜像构建
├── frontend/           # Vue3 前端应用
│   ├── src/            # 页面与组件 (Vue3 + Pinia + Router)
│   └── Dockerfile      # 前端镜像构建
├── judge/              # 判题沙箱环境配置
├── docker/             # 基础设施配置 (MySQL, Nginx)
└── docker-compose.yml  # 容器编排配置文件
```

## 🛠️ 技术栈

- **前端**：Vue 3, Vite, Pinia, Vue Router, Element Plus, Monaco Editor
- **后端**：Flask, SQLAlchemy (MySQL), JWT, Docker SDK for Python
- **基础设施**：Docker, Docker Compose, Nginx, MySQL 8.0

## 🚀 快速开始

### 前置要求
- 已安装 [Docker](https://www.docker.com/) 和 [Docker Compose](https://docs.docker.com/compose/)。

### 启动步骤
1. **克隆仓库**
   ```bash
   git clone https://github.com/your-repo/SKYOJ.git
   cd SKYOJ
   ```

2. **一键启动**
   ```bash
   docker-compose up --build
   ```

3. **访问系统**
   - 前端地址：`http://localhost`
   - 后端 API：`http://localhost:5000`
   - 数据库：`localhost:3306` (用户: root, 密码: root)

## 📈 当前进度

- [x] **Docker 容器化**：全栈容器化编排已完成。
- [x] **后端核心**：JWT 认证、题目管理、异步判题调度框架。
- [x] **判题模式**：ACM、OOP 模式已初步实现。
- [x] **前端基础**：题目列表、详情、提交、个人中心等核心页面。
- [ ] **管理后台**：教师端题目发布与数据管理界面完善中。
- [ ] **安全加固**：判题沙箱的资源限制（CPU/Memory）与网络隔离优化。

## 📄 开源协议
[MIT License](LICENSE)
