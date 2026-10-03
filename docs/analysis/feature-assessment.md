# SKYOJ 优化方向逐项现状评估

> 评估基准：仓库 `master` 分支（commit `b253d14`）的实际代码。
> 状态标识：✅ 已实现 / 🟡 部分实现 / ❌ 未实现 / ➖ 不适用

> **重要前置结论**：原始清单中很多方向已经在最近 8 次提交中落地（WebSocket 实时判题、Redis 限流、ACM 并发判题、JPlag 查重、Redis 排行榜缓存、pytest 套件、GitHub Actions CI）。在按清单评估前先说明这一点，避免重复造轮子。

---

## 一、高价值新功能（教学增强）

### 1. 题目讨论区 / 题解分享

| 项 | 状态 | 证据 |
|---|---|---|
| 学生发布题解（Markdown + 代码） | ❌ | 无 `discussion` / `solution_post` / `answer` / `comment` 模型；Grep 后端、前端无任何匹配 |
| 点赞 / 评论 / 收藏 | ❌ | 同上 |
| 教师加精 | ❌ | 同上 |
| 题解与提交双向关联 | ❌ | submission 模型无外键指向题解 |

**建议**：新增 `solution_posts / solution_likes / solution_comments / solution_favorites` 四张表；题目详情页增加"题解"标签页；提交 Accepted 后在 `SubmissionDetailView` 显示"发布题解"入口。

### 2. 比赛模式（Contest）

| 项 | 状态 | 证据 |
|---|---|---|
| ACM/ICPC 赛制判题 | ✅ | `services/acm.py:run_acm_judge` 全过/不过制 |
| 实时滚榜 + 罚时 | ✅ | `services/exam.py:rank()` 实现 ICPC 规则：solved 数 + penalty = elapsed + failed_attempts × 1200s；排序 `(-solved, penalty)` |
| 缓存优化 | ✅ | `utils/exam_cache.py` 60s TTL，判题完成时主动失效 |
| 封榜（最后一小时隐藏提交） | ❌ | rank() 直接用 `list_submissions`，无时间窗口过滤参数 |
| 打星团队 / 校外参赛者 | ❌ | `users` 表无 `is_guest / is_star / team_id` 字段 |
| 气球发放状态 | ❌ | 无 `balloon_status` 字段 |
| 实时滚动（WebSocket） | ❌ | rank 仅在 60s TTL 后或失效时刷新；无推送 |

**建议**：在 `Exam` 表加 `freeze_time / contest_type(contest/exam)`；rank() 增加 `as_of` 参数；增加 `monitor` 的 WebSocket 推送；考试管理员面板加气球状态网格。

### 3. 作业（Homework）模式

| 项 | 状态 | 证据 |
|---|---|---|
| 补交 / 迟交扣分 | ❌ | `Exam` 表无 `allow_late / late_penalty_percent` 字段 |
| 学生互评 | ❌ | 无 `peer_review` 模型 |
| 自动批改 | ✅ | 已有判题链路 |
| 教师统计 | 🟡 | `export_scores` CSV 已实现，但无提交率/平均分等聚合 |
| 截止后查看优秀作业 | ❌ | 无"精选提交"机制 |

**建议**：考虑将 `Exam` 模型扩展（增加 `type` 字段 `exam/contest/homework`）而非新建表，复用现有 `ExamProblem` 关联；补交逻辑在 `submit` 时计算 score 折算。

### 4. 题目标签 / 知识点体系

| 项 | 状态 | 证据 |
|---|---|---|
| 题目 tags 字段 | ❌ | `Problem` 模型只有 title/content/type/language/time/memory/template_code/test_case_path |
| 知识点树 | ❌ | 无 `knowledge_point` 表 |
| 按标签筛选 | ❌ | `ProblemRepository.list_all` 不支持 tag 过滤 |
| 知识点掌握度雷达图 | ❌ | 无相关数据/视图 |

**建议**：新增 `tags` / `knowledge_points` 两张关联表（`problem_tags` / `problem_knowledge_points`），Admin 题目表单加标签输入，学生 Profile 加雷达图（用 ECharts）。

### 5. 错题本 / 练习历史

| 项 | 状态 | 证据 |
|---|---|---|
| 自动归档错题 | ❌ | 无 `wrong_book` 表 |
| 重做 | ❌ | 无"重做此题"接口/入口 |
| 复习提醒（艾宾浩斯） | ❌ | 无相关任务 |
| 按错题生成练习卷 | ❌ | 同上 |

**建议**：可监听 `Submission.status` 在 `Wrong Answer / TLE / RE` 时写 `wrong_book` 行；复习提醒由 Celery beat 定时任务扫描。

---

## 二、教学辅助增强

### 6. AI 智能助教（聊天式）

| 项 | 状态 | 证据 |
|---|---|---|
| AI 出题 | ✅ | `services/llm_prompts.PROBLEM_GENERATION_*`，异步草稿箱 |
| AI 生成测例脚本 | ✅ | `TEST_SCRIPT_MODE_CONFIGS`，覆盖 acm/oop/kaggle |
| AI 解释错误 | ❌ | `services/llm.AskLlmParams` 只支持 system/prompt/output_format，无提交上下文 |
| AI 答疑（结合题目上下文） | ❌ | 同上 |
| AI 代码 review | ❌ | 无 |
| SSE 流式输出 | ❌ | AI 草稿箱只能轮询 `drafts/{id}` 看 status |

**建议**：扩展 `AskLlmBody` 支持 `context_submission_id`；新增 SSE 端点 `GET /api/llm/drafts/{id}/stream`（FastAPI `StreamingResponse`），前端用 `EventSource` 消费。

### 7. 学情看板 / 教师驾驶舱

| 项 | 状态 | 证据 |
|---|---|---|
| 全局统计卡片 | 🟡 | `TeacherDashboardView.vue:14-32` 显示总题目/活跃考试/今日提交/总用户数 4 个数字 |
| 班级维度（完成率/平均分/薄弱知识点） | ❌ | 无班级概念，无聚合 API |
| 题目维度（通过率/典型错误） | 🟡 | `SubmissionAdminView` 可看列表，无通过率分布 |
| 时间维度（每日活跃/提交热力） | ✅ | `SubmissionHeatmap.vue` 已实现，但只在某个详情页出现 |
| 导出 PDF 教学报告 | ❌ | `export_scores` 只导出 CSV |
| 薄弱知识点热力图 | ❌ | 无知识点维度 |

**建议**：先做轻量的——把 `SubmissionHeatmap` 放进 `TeacherDashboardView`，新增 `/admin/analytics` 页（题目通过率 + 错题错误类型 Top N）。

### 8. 学生互评 / Peer Review

| 项 | 状态 | 证据 |
|---|---|---|
| 匿名分配 / 评分 / 评语 | ❌ | 无任何相关模型 |
| 教师复核 | ❌ | 同上 |

**建议**：可作为 Homework 模式的一部分，新表 `peer_reviews(assignment_id, reviewer_id, reviewee_id, score, comment, teacher_reviewed)`。

### 9. 题目推荐系统

| 项 | 状态 | 证据 |
|---|---|---|
| 历史提交分析 | ❌ | 无 |
| 协同过滤 / 内容相似度 | ❌ | 无 |

**建议**：远期方向，可先做基于"做错题同 tag 的简单题目推荐"，不引入向量库。

---

## 三、判题与系统性能

### 10. 实时反馈机制

| 项 | 状态 | 证据 |
|---|---|---|
| WebSocket 判题推送 | ✅ | `api/submission.py:29 submission_websocket` + `utils/realtime.py` + 前端 `utils/websocket.js` |
| WebSocket 自动重连 | ❌ | `utils/websocket.js:17` 声明常量但未使用 |
| AI 草稿 SSE 流式 | ❌ | 只能轮询草稿箱 |
| 考试监控实时滚动 | ❌ | rank 走 60s TTL 缓存，无推送 |

### 11. 前端体验

| 项 | 状态 | 证据 |
|---|---|---|
| Monaco Editor | ✅ | `@guolao/vue-monaco-editor` 1.6 已集成 |
| 代码自动补全 / 标准库 | ❌ | 默认 Monaco + 当前语言，无定制 snippets |
| Vim/Emacs 模式 | ❌ | 无 monaco-vim 等 |
| 路由懒加载 | ✅ | `router/index.js` 全部 `() => import(...)` |
| 骨架屏 | 🟡 | 部分页面有 |
| PWA / IndexedDB 离线 | ❌ | 无 vite-plugin-pwa |

### 12. 判题性能

| 项 | 状态 | 证据 |
|---|---|---|
| ACM 并发容器 | ✅ | `services/acm.py:413-431` ThreadPoolExecutor，最多 8 并发 |
| 编译缓存 | ❌ | `acm.py:354` 注释明说"编译结果不跨容器复用" |
| warm pool 复用容器 | ❌ | 每次启动新容器 |
| OOP / Kaggle 并发 | ❌ | 未知，需进一步核对（按 Git 提交仅 ACM 有并发改造） |

**建议**：warm pool 改动较大（容器生命周期管理 + 安全），可考虑仅对编译产物做 cache（按 `language + code_hash` 缓存 .class / .o）。

---

## 四、评测能力

### 13. 多语言支持

| 语言 | 状态 |
|---|---|
| C / C++ / Java / Python | ✅ `acm.py:_ACM_LANG_CONFIGS` |
| Go / Rust / JavaScript | ❌ |

### 14. 评测模式

| 模式 | 状态 |
|---|---|
| ACM (Std I/O) | ✅ |
| OOP (单元测试) | ✅ |
| Kaggle (CSV Metric) | ✅ |
| Special Judge | ❌ |
| Interactive | ❌ |
| Output Only | ❌ |
| OI 按点给分 | 🟡 实际已按点给分（`acm.py:453` `passed_count/total_cases*100`），但状态枚举里没有"Partial Score"，统一报 Wrong Answer / TLE |

**建议**：
- SPJ：增加 problem.type=`spj`，judge 流程跑完后调用 SPJ 容器
- OI：在 submission.status 增加 `"Partial Score"`；前端按状态显示得分进度条

---

## 五、工程与稳定性

### 15. 可观测性

| 项 | 状态 | 证据 |
|---|---|---|
| Prometheus / Grafana | ❌ | 无 |
| 结构化日志聚合（ELK/Loki） | ❌ | 仅 Loguru stdout |
| 告警（队列积压/Worker 异常） | ❌ | 无 |
| 健康检查 | 🟡 | `/healthz` 返回 `{"status": "ok"}`，无依赖检查 |

### 16. 缓存与查询优化

| 项 | 状态 | 证据 |
|---|---|---|
| 排行榜 Redis Sorted Set | 🟡 | `exam_cache.py` 用 `set/get`，**没用 Sorted Set**；TTL 60s 简单粗暴 |
| 题目详情 Markdown 缓存 | ❌ | 每次 SQL 查询 content |
| 数据库索引审计 | 🟡 | submission/exam 有部分索引，未做完整审计 |
| N+1 优化 | ✅ | `031471d perf(backend): eliminate exam N+1 queries` |

**建议**：
- 排行榜改 Redis Sorted Set（ZADD score:user + ZRANGE），避免 TTL 边界失效
- 题目 Markdown 在 `services/problem_service.get_detail` 加 Redis 缓存，发布/编辑时失效

### 17. 安全加固

| 项 | 状态 | 证据 |
|---|---|---|
| 限流 | ✅ | 登录 5/60s、注册 3/60s、提交 10/60s |
| 审计日志 | ✅ | 全部 POST/PUT/DELETE/PATCH 自动审计 |
| API 挂 docker.sock | ✅ **已修复** | 只有 judge-worker 挂，security-debt.md 没更新 |
| 考试防作弊 | ❌ | 无切屏检测/复制粘贴监控 |
| 代码注入防护 | 🟡 | 沙箱隔离有，**无静态扫描**（检测 fork/exec/网络调用） |

---

## 六、测试与质量

### 18. 自动化测试

| 项 | 状态 | 证据 |
|---|---|---|
| 后端单元测试 | ✅ | 19 个测试文件，service / mapper / auth / job / queue |
| API 集成测试 | 🟡 | `test_auth_api.py` 等覆盖部分 |
| 前端组件测试 | ❌ | 无 Vitest 配置 |
| E2E（Playwright） | ❌ | 无 |
| 判题结果回归测试 | ❌ | 无 |
| CI 跑测试 | ✅ | `.github/workflows/ci.yml` backend-tests + frontend-build + compose-config |

### 19. CI/CD

| 项 | 状态 | 证据 |
|---|---|---|
| GitHub Actions lint + test + build | ✅ | CI 已就位 |
| 镜像构建推送 | ❌ | 无 docker publish workflow |
| API 版本控制 | ❌ | URL 全部 `/api/...` 无 `/v1` |

---

## 七、UX 细节

### 20. 提交体验

| 项 | 状态 | 证据 |
|---|---|---|
| 代码历史版本 | ❌ | submission 只保留单条记录 |
| CE 错误友好展示 | 🟡 | submission.output_log 含原始编译器输出，前端按行展示 |
| Test Case 详情 | ❌ | submission.output_log 只聚合文本，无结构化（ACM 单点调试有，提交整体没有） |
| 代码 diff | ❌ | 无 |

**建议**：在 `Submission` 模型加 `case_results JSON` 字段保存逐点结果（passed/wrong/tle/re 状态 + 行数），前端按点折叠。

### 21. 考试功能

| 项 | 状态 | 证据 |
|---|---|---|
| 题目难度 / 分类 | ❌ | 无 tags / difficulty |
| 题目收藏 | ❌ | 无 |
| 多教师协作 | ❌ | `Exam.created_by` 是单值 |
| 考试模板 | ❌ | 无复制功能 |

### 22. 移动端 / PWA

| 项 | 状态 | 证据 |
|---|---|---|
| 响应式 | 🟡 | `@media (max-width: 768px)` 在部分组件 |
| PWA / 离线 | ❌ | 无 |
| 小程序 | ❌ | 无 |

---

## 八、可直接拉开的差距（重新排序）

按"对教学价值 × 实现难度"评估，给你一份**真正优先级**清单（结合实际已实现状态）：

### P0：3-5 天可做，立竿见影

1. **修复错误码格式不一致**（`utils/request.js` 改读 `error` 或后端加 `code` 字段）
2. **WebSocket 自动重连**（`utils/websocket.js` 加 onclose → setTimeout reconnect）
3. **修正 `docs/security-debt.md`**（删除/标记里程碑 2 已完成）
4. **FastAPI `on_event` → `lifespan`**（`main.py:157`）
5. **题目 Markdown Redis 缓存**（5 行代码）
6. **`Submission.case_results JSON` 字段**（让 ACM 提交也能展示逐点结果）

### P1：2-4 周，教学价值高

7. **题解分享 / 讨论区**（4 张表 + 题目详情 Tab + Submission Detail 入口）
8. **题目标签 + 知识点**（含标签筛选 / 知识点筛选）
9. **考试 → 比赛模式扩展**（在 `Exam` 表加 `contest_type / freeze_time`，rank() 加 `as_of`）
10. **学情看板增强**（通过率分布 + SubmissionHeatmap 复用）
11. **AI 答疑 / 代码 review**（扩展 `AskLlmParams`，新增 SSE 流式）
12. **E2E 测试 + 前端组件测试**（Vitest + Playwright）

### P2：1-2 月，规模化

13. **作业（Homework）模式**（复用 `Exam` 模型扩展 `type`）
14. **错题本**（监听 submission 状态变更写 `wrong_book` 表）
15. **SPJ / OI 按点给分**（submission.status 增加 `"Partial Score"`）
16. **编译缓存 / Warm Pool**（按 code_hash 缓存 .class/.o）
17. **Prometheus + Grafana**（FastAPI `prometheus-fastapi-instrumentator`，Celery metrics 走 RabbitMQ exporter）
18. **考试防作弊**（前端切屏检测 → 提交审计事件）

### P3：远期

19. 互评 / 推荐系统 / 多语言扩展（Go/Rust/JS）/ 移动端
