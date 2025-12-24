# SKYOJ API 接口文档

本文档详细说明了 SKYOJ 系统后端的 RESTful API 接口。

## 1. 基础信息

- **Base URL**: `http://<host>:<port>/api` (开发环境下通常为 `http://localhost:5000/api`)
- **Content-Type**: `application/json` (文件上传接口除外)
- **认证方式**: 使用 JWT (JSON Web Token)。除登录/注册外，大部分接口需要在 Header 中携带：
  `Authorization: Bearer <your_token>`

---

## 2. 用户认证模块 (Auth)

### 2.1 用户注册
- **URL**: `/auth/register`
- **Method**: `POST`
- **Auth Required**: No
- **Request Body**: `{"username": "test", "password": "...", "role": "student"}`

### 2.2 用户登录
- **URL**: `/auth/login`
- **Method**: `POST`
- **Auth Required**: No
- **Success Response**: 返回 `token` 和用户信息。

---

## 3. 题目管理模块 (Problems)

### 3.1 题目基础操作
- **URL**: `/problems/` 或 `/problems/<id>`
- **Methods**: `POST`, `GET`, `PUT`, `DELETE`
- **Auth Required**: 管理类操作需 Teacher 权限。

### 3.2 测试点管理 (Test Cases)
- **上传测试点 (Zip)**: 
  - **URL**: `/problems/<id>/upload_files`
  - **Method**: `POST`
  - **Body**: `multipart/form-data` (Key: `file`)
- **下载所有测试点**:
  - **URL**: `/problems/<id>/test_cases`
  - **Method**: `GET`
  - **Auth Required**: Teacher only
  - **Response**: 返回 ZIP 压缩包文件流。
- **删除所有测试点**:
  - **URL**: `/problems/<id>/test_cases`
  - **Method**: `DELETE`
  - **Auth Required**: Teacher only

---

## 4. 提交与判题模块 (Submissions)

### 4.1 提交代码
- **URL**: `/submissions/submit`
- **Method**: `POST`
- **Request Body**: `{"problem_id": 1, "code": "...", "language": "python"}`
- **Success Response**: `202 Accepted`

### 4.2 获取提交详情
- **URL**: `/submissions/<submission_id>`
- **Method**: `GET`

---

## 5. 考试模块 (Exams)
*详见原文档，支持创建、加密验证、题目绑定等操作。*

---

## 6. 系统配置模块 (SysDict)

### 6.1 获取/更新系统配置
- **URL**: `/sys/info`
- **Methods**: `GET`, `PUT` (Teacher only)
- **常用 Key**: `tile`, `llm_api_key`, `llm_api_url`, `llm_model_name` 等。

---

## 7. 智能助手模块 (LLM)

### 7.1 调用 LLM 接口
- **URL**: `/llm/ask`
- **Method**: `POST`
- **Auth Required**: Yes
- **Request Body**:
  ```json
  {
    "system_setting": "你是一个代码助手",
    "prompt": "解释这段代码...",
    "output_format": { "explanation": "string" } 
  }
  ```
- **Note**: 配置（API Key 等）由后端自动从 `SysDict` 中读取。

---

## 8. 数据集模块 (Datasets)
*支持列表获取、上传、下载（支持 URL Token）及删除。*
