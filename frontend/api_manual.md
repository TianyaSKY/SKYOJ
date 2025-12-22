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
  *注：role 可选值为 'student' 或 'teacher'，默认为 'student'。*
- **Success Response**: `201 Created`
  ```json
  { "message": "User registered successfully" }
  ```

### 2.2 用户登录
- **URL**: `/auth/login`
- **Method**: `POST`
- **Auth Required**: No
- **Request Body**:
  ```json
  {
    "username": "testuser",
    "password": "password123"
  }
  ```
- **Success Response**: `200 OK`
  ```json
  {
    "message": "Login successful",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 1,
      "username": "testuser",
      "role": "student"
    }
  }
  ```

---

## 3. 题目管理模块 (Problems)

### 3.1 创建题目
- **URL**: `/problems/`
- **Method**: `POST`
- **Auth Required**: No (建议后续增加权限校验)
- **Request Body**:
  ```json
  {
    "title": "A+B Problem",
    "content": "Calculate the sum of two integers.",
    "language": "python",
    "type": "acm",
    "time_limit": 1000,
    "memory_limit": 128,
    "template_code": ""
  }
  ```
- **Success Response**: `201 Created`
  ```json
  { "message": "Problem created successfully", "problem_id": 1 }
  ```

### 3.2 获取题目列表
- **URL**: `/problems/`
- **Method**: `GET`
- **Auth Required**: No
- **Success Response**: `200 OK`
  ```json
  [
    { "id": 1, "title": "A+B Problem", "type": "acm" }
  ]
  ```

### 3.3 获取题目详情
- **URL**: `/problems/<problem_id>`
- **Method**: `GET`
- **Auth Required**: No
- **Success Response**: `200 OK`
  ```json
  {
    "id": 1,
    "title": "A+B Problem",
    "content": "...",
    "type": "acm",
    "language": "python",
    "time_limit": 1000,
    "memory_limit": 128,
    "template_code": ""
  }
  ```

### 3.4 更新题目
- **URL**: `/problems/<problem_id>`
- **Method**: `PUT`
- **Auth Required**: No
- **Request Body**: 同创建题目
- **Success Response**: `200 OK`
  ```json
  { "message": "Problem updated successfully" }
  ```

### 3.5 删除题目
- **URL**: `/problems/<problem_id>`
- **Method**: `DELETE`
- **Auth Required**: No
- **Success Response**: `200 OK`
  ```json
  { "message": "Problem deleted successfully" }
  ```

### 3.6 上传测试用例 (Zip)
- **URL**: `/problems/<problem_id>/upload_files`
- **Method**: `POST`
- **Auth Required**: No
- **Request Body**: `multipart/form-data` (Key: `file`, Value: `testcases.zip`)
- **Success Response**: `200 OK`
  ```json
  {
    "message": "Test cases for problem 1 uploaded and extracted successfully.",
    "files": ["1.in", "1.out", "2.in", "2.out"]
  }
  ```
  *注：上传新压缩包会清空该题目原有的所有测试文件。*

---

## 4. 提交与判题模块 (Submissions)

### 4.1 提交代码
- **URL**: `/submissions/submit`
- **Method**: `POST`
- **Auth Required**: Yes
- **Request Body**:
  - **JSON 方式**:
    ```json
    {
      "problem_id": 1,
      "code": "print(sum(map(int, input().split())))",
      "language": "python"
    }
    ```
  - **Form-data 方式**: 
    - `problem_id`: 题目ID
    - `language`: 编程语言
    - `code`: 代码字符串 (可选)
    - `file`: 源码文件 (可选，若提供则优先于 `code` 字段)
- **Success Response**: `202 Accepted`
  ```json
  {
    "message": "Submission received, judging in background.",
    "submission_id": 10,
    "status": "Pending"
  }
  ```

### 4.2 获取提交详情
- **URL**: `/submissions/<submission_id>`
- **Method**: `GET`
- **Auth Required**: Yes
- **Success Response**: `200 OK`
  ```json
  {
    "id": 10,
    "status": "Accepted",
    "score": 100.0,
    "log": "Test Case 1: Passed...",
    "code": "...",
    "language": "python",
    "created_at": "2023-10-27T10:00:00"
  }
  ```

---

## 5. 用户模块 (User)

### 5.1 获取当前用户提交记录
- **URL**: `/user/submissions`
- **Method**: `GET`
- **Auth Required**: Yes
- **Success Response**: `200 OK`
  ```json
  [
    {
      "id": 10,
      "problem_id": 1,
      "problem_title": "A+B Problem",
      "status": "Accepted",
      "score": 100.0,
      "language": "python",
      "created_at": "2023-10-27T10:00:00"
    }
  ]
  ```

---

## 6. 数据集模块 (Datasets)

### 6.1 获取数据集列表
- **URL**: `/datasets`
- **Method**: `GET`
- **Auth Required**: No
- **Success Response**: `200 OK`
  ```json
  [
    {
      "id": 1,
      "name": "MNIST",
      "description": "Handwritten digits dataset",
      "file_size": "11.06 MB",
      "created_at": "2023-10-27T10:00:00"
    }
  ]
  ```

### 6.2 上传数据集
- **URL**: `/datasets`
- **Method**: `POST`
- **Auth Required**: No (建议后续增加教师权限校验)
- **Request Body**: `multipart/form-data`
  - `file`: 数据集文件 (必填)
  - `name`: 数据集名称
  - `description`: 数据集描述
- **Success Response**: `201 Created`
  ```json
  {
    "id": 1,
    "name": "MNIST",
    "description": "...",
    "file_size": "11.06 MB",
    "file_path": "uploads/datasets/mnist.zip"
  }
  ```

### 6.3 下载数据集
- **URL**: `/datasets/<id>/download`
- **Method**: `GET`
- **Auth Required**: No
- **Success Response**: `200 OK` (直接返回文件二进制流，浏览器触发下载)
