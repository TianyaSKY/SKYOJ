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
- **Request Body**:
  ```json
  {
    "username": "testuser",
    "password": "password123",
    "role": "student" 
  }
  ```
- **Success Response**: `201 Created`

### 2.2 用户登录
- **URL**: `/auth/login`
- **Method**: `POST`
- **Auth Required**: No
- **Success Response**: `200 OK` (返回 token 和用户信息)

---

## 3. 题目管理模块 (Problems)

### 3.1 创建/获取/更新/删除题目
- **URL**: `/problems/` 或 `/problems/<id>`
- **Methods**: `POST`, `GET`, `PUT`, `DELETE`
- **Auth Required**: No (建议教师权限)

### 3.2 上传测试用例 (Zip)
- **URL**: `/problems/<problem_id>/upload_files`
- **Method**: `POST`
- **Request Body**: `multipart/form-data` (Key: `file`)

---

## 4. 提交与判题模块 (Submissions)

### 4.1 提交代码
- **URL**: `/submissions/submit`
- **Method**: `POST`
- **Auth Required**: Yes
- **Request Body**:
  - **JSON**: `{"problem_id": 1, "code": "...", "language": "python", "exam_id": null}`
  - **Form-data**: 支持 `file` 字段上传源码文件。
- **Success Response**: `202 Accepted`

### 4.2 获取提交详情
- **URL**: `/submissions/<submission_id>`
- **Method**: `GET`
- **Auth Required**: Yes

---

## 5. 考试模块 (Exams)

### 5.1 创建考试
- **URL**: `/exams/`
- **Method**: `POST`
- **Auth Required**: Yes (Teacher only)
- **Request Body**:
  ```json
  {
    "title": "期中考试",
    "description": "2023秋季期中测试",
    "start_time": "2023-11-01T09:00:00",
    "end_time": "2023-11-01T11:00:00",
    "password": "123",
    "is_visible": true
  }
  ```
  *注：后端会对 password 进行哈希存储。*

### 5.2 获取考试列表
- **URL**: `/exams/`
- **Method**: `GET`
- **Auth Required**: Yes
- **Success Response**: `200 OK` (学生仅能看到 `is_visible=true` 的考试)

### 5.3 获取考试详情 (含题目)
- **URL**: `/exams/<exam_id>`
- **Method**: `GET`
- **Auth Required**: Yes
- **Success Response**:
  ```json
  {
    "id": 1,
    "title": "...",
    "has_password": true,
    "problems": [
      { "problem_id": 10, "display_id": "A", "score": 100, "title": "A+B" }
    ]
  }
  ```
  *注：`has_password` 用于前端判断是否需要弹出密码输入框。*

### 5.4 验证考试密码
- **URL**: `/exams/<exam_id>/verify`
- **Method**: `POST`
- **Auth Required**: Yes
- **Request Body**: `{"password": "123"}`
- **Success Response**: `200 OK` (`{"message": "Password verified"}`)
- **Error Response**: `401 Unauthorized` (`{"error": "Incorrect password"}`)

### 5.5 考试题目管理 (Teacher only)
- **添加题目**: `POST /exams/<exam_id>/problems` (Body: `{"problem_id": 1, "display_id": "A", "score": 100}`)
- **移除题目**: `DELETE /exams/<exam_id>/problems/<problem_id>`

---

## 6. 数据集模块 (Datasets)

### 6.1 获取列表/上传/下载/删除
- **获取列表**: `GET /datasets`
- **上传**: `POST /datasets` (Multipart, Teacher only)
- **下载**: `GET /datasets/<id>/download?token=<jwt_token>` (支持 URL 参数 Token)
- **删除**: `DELETE /datasets/<id>` (Teacher only)

---

## 7. 用户模块 (User)

### 7.1 获取当前用户提交记录
- **URL**: `/user/submissions`
- **Method**: `GET`
- **Auth Required**: Yes
