# SKYOJ

SKYOJ 是一个基于 Vue3 + Flask + MySQL + Docker 构建的在线评测系统（Online Judge）。它不仅支持传统的 ACM 判题模式，还针对教学场景设计了面向对象（OOP）测试模式和数据科学竞赛（Kaggle）模式。

## 🌟 核心特性

- **多模式判题**：
  - **ACM 模式**：标准输入输出比对。
  - **OOP 模式**：基于单元测试（unittest/pytest）的代码片段评测。
  - **Kaggle 模式**：基于 CSV 文件的结果评分，支持自定义评分脚本。
- **智能查重 (Plagiarism Detection)**：集成 `sentence-transformers` 深度学习模型，支持基于向量相似度的代码查重。
- **智能助手 (LLM)**：集成 DeepSeek 等大模型，支持思维链（Thinking）推理，辅助学生理解题目与代码。
- **容器化隔离**：所有用户提交的代码均在独立的 Docker 容器中运行，确保系统安全。
- **全栈部署**：提供完整的 Docker Compose 配置，实现一键本地或服务器部署。

## 📂 项目结构

```text
SKYOJ/
├── backend/            # Flask 后端应用
│   └── sandbox/        # 判题沙箱镜像配置
│       ├── runners/    # skyoj-runner (执行用户代码)
│       └── random_data/# skyoj-generator (生成测试数据)
├── frontend/           # Vue3 前端应用
├── judge/              # 判题沙箱环境配置 (Legacy)
├── generate/           # 题目与数据生成工具脚本
├── docker/             # 基础设施配置 (MySQL, Nginx)
└── docker-compose.yml  # 容器编排配置文件
```

## 🚀 快速开始

### 1. 构建沙箱镜像 (必须)
在启动主系统前，需手动构建用于运行代码和生成数据的沙箱镜像：

```bash
# 构建判题运行环境镜像
docker build -t skyoj-runner ./backend/sandbox/runners

# 构建数据生成环境镜像
docker build -t skyoj-generator ./backend/sandbox/random_data
```

### 2. 启动系统
```bash
# 一键启动后端、前端、数据库及 Nginx
docker-compose up --build
```

### 3. 访问系统
- 前端：`http://localhost`
- 后端 API：`http://localhost:5000/api`

## 📈 当前进度

- [x] **Docker 容器化**：全栈容器化编排已完成。
- [x] **后端核心**：JWT 认证、题目管理、异步判题调度框架。
- [x] **智能助手**：集成 OpenAI SDK，支持 DeepSeek 推理模型及动态配置。
- [x] **智能查重**：基于深度学习的代码相似度检测服务已上线。
- [x] **判题模式**：ACM、OOP、Kaggle 模式核心逻辑已实现。
- [ ] **管理后台**：教师端题目管理、数据集管理 UI 进一步完善中。

## 📄 开源协议
[MIT License](LICENSE)
