# SKYOJ

SKYOJ 是一个基于 Vue3 + Flask + MySQL + Docker 构建的在线评测系统（Online Judge）。它不仅支持传统的 ACM
判题模式，还针对教学场景设计了面向对象（OOP）测试模式和数据科学竞赛（Kaggle）模式。

## 🌟 核心特性

- **多模式判题**：
    - **ACM 模式**：标准输入输出比对。
    - **OOP 模式**：基于单元测试（unittest/pytest）的代码片段评测。
    - **Kaggle 模式**：基于 CSV 文件的结果评分。
- **智能助手 (LLM)**：集成 DeepSeek 等大模型，支持思维链（Thinking）推理，辅助学生理解题目与代码。
- **容器化隔离**：所有用户提交的代码均在独立的 Docker 容器中运行，确保系统安全。
- **全栈部署**：提供完整的 Docker Compose 配置，实现一键本地或服务器部署。

## 📂 项目结构

```text
SKYOJ/
├── backend/            # Flask 后端应用 (API, Models, Services)
├── frontend/           # Vue3 前端应用 (Pinia, Router, Element Plus)
├── judge/              # 判题沙箱环境配置
├── docker/             # 基础设施配置 (MySQL, Nginx)
└── docker-compose.yml  # 容器编排配置文件
```

## 🛠️ 技术栈

- **前端**：Vue 3, Vite, Pinia, Element Plus, Monaco Editor
- **后端**：Flask, SQLAlchemy, JWT, OpenAI SDK (for LLM)
- **基础设施**：Docker, Docker Compose, Nginx, MySQL 8.0

## 🚀 快速开始

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
    - 前端：`http://localhost`
    - 后端 API：`http://localhost:5000/api`

## 📈 当前进度

- [x] **Docker 容器化**：全栈容器化编排已完成。
- [x] **后端核心**：JWT 认证、题目管理、异步判题调度框架。
- [x] **智能助手**：集成 OpenAI SDK，支持 DeepSeek 推理模型及动态配置。
- [x] **测试点管理**：支持 ZIP 上传、批量下载（内存压缩）及一键清空。
- [x] **判题模式**：ACM、OOP 模式已初步实现。
- [ ] **管理后台**：教师端 UI 交互完善中。

## 📄 开源协议

[MIT License](LICENSE)
