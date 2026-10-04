import { beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest'
import type { AxiosRequestConfig } from 'axios'
import type { ProblemDetailResponse } from '@/types/problem'
import type { SubmitCodeBody } from '@/types/submission'
import type { LoginInput } from '@/schemas/auth'
vi.mock('@/utils/request', () => ({ default: vi.fn() }))
import request from '@/utils/request'
import * as problem from '../problem'
import * as dataset from '../dataset'
import * as exam from '../exam'
import * as submission from '../submission'
import * as user from '../user'
import * as sys from '../sys'
import * as debug from '../debug'
import * as llm from '../llm'
import * as community from '../community'
import * as tag from '../tag'
import * as wrongBook from '../wrongBook'
import * as analytics from '../analytics'
import type { SolutionListResponse, CommentListResponse } from '@/types/community'
import type { WrongBookStatsResponse } from '@/types/wrongBook'
import type { PlatformAnalyticsResponse } from '@/types/analytics'
import type { SolutionFormInput } from '@/schemas/community'

const send = vi.mocked(request)
beforeEach(() => vi.resetAllMocks())

interface ContractCase {
  name: string
  invoke: () => Promise<unknown>
  config: AxiosRequestConfig
}

const code = { problem_id: 1, code: 'print(3)', language: 'python', exam_id: 2 }
const form = new FormData()
form.append('file', new Blob(['data']), 'test.txt')
const solutionForm: SolutionFormInput = {
  title: '题解',
  content: '    保留 Markdown 缩进',
  language: null,
}
const cases: ContractCase[] = [
  {
    name: '题解列表分页',
    invoke: () => community.getSolutions(42, { page: 2, page_size: 20 }),
    config: { url: '/problems/42/solutions', method: 'get', params: { page: 2, page_size: 20 } },
  },
  {
    name: '发布题解保留正文与空语言',
    invoke: () => community.createSolution(42, solutionForm),
    config: { url: '/problems/42/solutions', method: 'post', data: solutionForm },
  },
  {
    name: '修改题解',
    invoke: () => community.updateSolution(7, solutionForm),
    config: { url: '/problems/solutions/7', method: 'put', data: solutionForm },
  },
  {
    name: '隐藏题解',
    invoke: () => community.hideSolution(7),
    config: { url: '/problems/solutions/7', method: 'delete' },
  },
  {
    name: '题解点赞',
    invoke: () => community.toggleSolutionLike(7),
    config: { url: '/problems/solutions/7/like', method: 'post' },
  },
  {
    name: '题解收藏',
    invoke: () => community.toggleSolutionFavorite(7),
    config: { url: '/problems/solutions/7/favorite', method: 'post' },
  },
  {
    name: '评论列表分页',
    invoke: () => community.getComments(7, { page: 2, page_size: 50 }),
    config: {
      url: '/problems/solutions/7/comments',
      method: 'get',
      params: { page: 2, page_size: 50 },
    },
  },
  {
    name: '发布评论',
    invoke: () => community.createComment(7, { content: '评论' }),
    config: { url: '/problems/solutions/7/comments', method: 'post', data: { content: '评论' } },
  },
  {
    name: '删除评论',
    invoke: () => community.deleteComment(8),
    config: { url: '/problems/comments/8', method: 'delete' },
  },
  { name: '全部标签', invoke: () => tag.getTags(), config: { url: '/tags', method: 'get' } },
  {
    name: '题目标签',
    invoke: () => tag.getProblemTags(42),
    config: { url: '/tags/problems/42', method: 'get' },
  },
  {
    name: '教师直接批准标签',
    invoke: () => tag.attachProblemTag(42, { tag_id: 7, approved: true }),
    config: {
      url: '/tags/problems/42/attach',
      method: 'post',
      data: { tag_id: 7, approved: true },
    },
  },
  {
    name: '学生建议标签',
    invoke: () => tag.attachProblemTag(42, { tag_id: 7, approved: false }),
    config: {
      url: '/tags/problems/42/attach',
      method: 'post',
      data: { tag_id: 7, approved: false },
    },
  },
  {
    name: '移除标签',
    invoke: () => tag.detachProblemTag(42, 7),
    config: { url: '/tags/problems/42/7', method: 'delete' },
  },
  {
    name: '错题本统计',
    invoke: () => wrongBook.getWrongBookStats(),
    config: { url: '/wrong-book/stats', method: 'get' },
  },
  {
    name: '错题本列表保留尾斜杠',
    invoke: () => wrongBook.getWrongBook({ page: 2, page_size: 10 }),
    config: { url: '/wrong-book/', method: 'get', params: { page: 2, page_size: 10 } },
  },
  {
    name: '错题复习切换不携带请求体',
    invoke: () => wrongBook.toggleWrongBookReview(9),
    config: { url: '/wrong-book/9/toggle-review', method: 'post' },
  },
  {
    name: '平台分析统计',
    invoke: () => analytics.getPlatformAnalytics(),
    config: { url: '/admin/analytics', method: 'get' },
  },
  {
    name: '清空测例保留删除接口',
    invoke: () => problem.deleteAllTestCases(1),
    config: { url: '/problems/1/test_cases', method: 'delete' },
  },
  {
    name: '同步 AI 对话保留五分钟超时',
    invoke: () => llm.askLLM({ system_setting: '分析代码', prompt: 'print(3)' }),
    config: {
      url: '/llm/ask',
      method: 'post',
      data: { system_setting: '分析代码', prompt: 'print(3)' },
      timeout: 300000,
    },
  },
  {
    name: '异步执行测例脚本保留请求体与两分钟超时',
    invoke: () => llm.executeAndSubmitTestData({ problem_id: 1, code: 'print(3)' }),
    config: {
      url: '/llm/execute-test-generation',
      method: 'post',
      data: { problem_id: 1, code: 'print(3)' },
      timeout: 120000,
    },
  },
  {
    name: '题目列表分页与类别',
    invoke: () => problem.getProblemList({ page: 2, problem_type: 'acm' }),
    config: { url: '/problems/', method: 'get', params: { page: 2, problem_type: 'acm' } },
  },
  {
    name: '搜索参数',
    invoke: () => problem.searchProblems({ query: 'abc', top_k: 5 }),
    config: { url: '/search', method: 'get', params: { query: 'abc', top_k: 5 } },
  },
  {
    name: '题目详情',
    invoke: () => problem.getProblemDetail(1),
    config: { url: '/problems/1', method: 'get' },
  },
  {
    name: '局部更新保留 null',
    invoke: () => problem.updateProblem(1, { memory_limit: null }),
    config: { url: '/problems/1', method: 'put', data: { memory_limit: null } },
  },
  {
    name: 'JSON 提交',
    invoke: () => problem.submitSolution(code),
    config: {
      url: '/submissions/submit',
      method: 'post',
      data: code,
      timeout: 120000,
      headers: undefined,
    },
  },
  {
    name: '文件提交',
    invoke: () => problem.submitSolution(form),
    config: {
      url: '/submissions/submit',
      method: 'post',
      data: form,
      timeout: 120000,
      headers: { 'Content-Type': 'multipart/form-data' },
    },
  },
  {
    name: '测例上传',
    invoke: () => problem.uploadTestCases(1, form),
    config: {
      url: '/problems/1/upload_files',
      method: 'post',
      data: form,
      timeout: 300000,
      headers: { 'Content-Type': 'multipart/form-data' },
    },
  },
  {
    name: '测例下载 Blob',
    invoke: () => problem.downloadTestCases(1),
    config: { url: '/problems/1/test_cases', method: 'get', responseType: 'blob' },
  },
  {
    name: '数据集列表',
    invoke: () => dataset.getDatasetList({ page_size: 10 }),
    config: { url: '/datasets', method: 'get', params: { page_size: 10 } },
  },
  {
    name: '数据集上传',
    invoke: () => dataset.uploadDataset(form),
    config: {
      url: '/datasets',
      method: 'post',
      data: form,
      timeout: 300000,
      headers: { 'Content-Type': 'multipart/form-data' },
    },
  },
  {
    name: '数据集下载',
    invoke: () => dataset.downloadDataset(1),
    config: { url: '/datasets/1/download', method: 'get', responseType: 'blob', timeout: 300000 },
  },
  {
    name: '考试密码清空',
    invoke: () => exam.updateExam(2, { password: null }),
    config: { url: '/exams/2', method: 'put', data: { password: null } },
  },
  {
    name: '考试进入',
    invoke: () => exam.enterExam(2, 'pwd'),
    config: { url: '/exams/2/enter', method: 'post', data: { password: 'pwd' } },
  },
  {
    name: '考试退出',
    invoke: () => exam.exitExam(),
    config: { url: '/exams/exit', method: 'post' },
  },
  {
    name: '考试成绩 Blob',
    invoke: () => exam.exportExamScores(2),
    config: { url: '/exams/2/export_scores', method: 'get', responseType: 'blob' },
  },
  {
    name: '提交历史筛选',
    invoke: () => submission.getSubmissions({ username: 'alice', exam_id: 2 }),
    config: { url: '/submissions', method: 'get', params: { username: 'alice', exam_id: 2 } },
  },
  {
    name: '当前用户提交',
    invoke: () => user.getUserSubmissions(),
    config: { url: '/user/submissions', method: 'get' },
  },
  {
    name: '指定用户提交',
    invoke: () => user.getUserSubmissions(3),
    config: { url: '/user/3/submissions', method: 'get' },
  },
  {
    name: '注册请求',
    invoke: () => user.register({ username: 'alice', password: 'abcdef' }),
    config: {
      url: '/auth/register',
      method: 'post',
      data: { username: 'alice', password: 'abcdef' },
    },
  },
  {
    name: '系统动态配置',
    invoke: () => sys.updateSysInfo({ practice: false, title: 'OJ' }),
    config: { url: '/sys/info', method: 'put', data: { practice: false, title: 'OJ' } },
  },
  {
    name: '调试请求',
    invoke: () => debug.debugSolution(code),
    config: { url: '/debug', method: 'post', data: code },
  },
  {
    name: 'AI 草稿列表',
    invoke: () => llm.listAiDrafts({ status: 'success', limit: 5 }),
    config: { url: '/llm/drafts', method: 'get', params: { status: 'success', limit: 5 } },
  },
  {
    name: 'AI 出题请求',
    invoke: () => llm.submitProblemGenerationDraft({ background: '排序', difficulty: '简单' }),
    config: {
      url: '/llm/drafts/problem-generation',
      method: 'post',
      data: { background: '排序', difficulty: '简单' },
      timeout: 30000,
    },
  },
]

describe('领域 API 保持现有 HTTP 契约', () => {
  it.each(cases)('$name', async ({ invoke, config }) => {
    const response = { message: 'ok' }
    send.mockResolvedValueOnce(response)
    expect(await invoke()).toBe(response)
    expect(send).toHaveBeenCalledExactlyOnceWith(config)
  })
  it('无正文写操作保留空响应语义，失败不被包装或吞掉', async () => {
    send.mockResolvedValueOnce(undefined)
    expect(await tag.detachProblemTag(42, 7)).toBeUndefined()
    const failure = { response: { status: 403, data: { error: '无权访问' } } }
    send.mockRejectedValueOnce(failure)
    await expect(community.createComment(7, { content: '评论' })).rejects.toBe(failure)
    expect(send).toHaveBeenLastCalledWith({
      url: '/problems/solutions/7/comments',
      method: 'post',
      data: { content: '评论' },
    })
  })
  it('新领域 API 的输入输出具有明确类型', () => {
    expectTypeOf(community.getSolutions).returns.toEqualTypeOf<Promise<SolutionListResponse>>()
    expectTypeOf(community.getComments).returns.toEqualTypeOf<Promise<CommentListResponse>>()
    expectTypeOf(community.createSolution).parameter(1).toEqualTypeOf<SolutionFormInput>()
    expectTypeOf(tag.attachProblemTag)
      .parameter(1)
      .toEqualTypeOf<{ tag_id: number; approved: boolean }>()
    expectTypeOf(tag.detachProblemTag).returns.toEqualTypeOf<Promise<void>>()
    expectTypeOf(wrongBook.getWrongBookStats).returns.toEqualTypeOf<
      Promise<WrongBookStatsResponse>
    >()
    expectTypeOf(analytics.getPlatformAnalytics).returns.toEqualTypeOf<
      Promise<PlatformAnalyticsResponse>
    >()
    expectTypeOf(sys).not.toHaveProperty('rebuildIndex')
  })
  it('下载结果保持 Blob，文件表单保持同一实例', async () => {
    const blob = new Blob(['case data'])
    send.mockResolvedValueOnce(blob)
    expect(await problem.downloadTestCases(1)).toBe(blob)
    send.mockResolvedValueOnce({ message: 'ok' })
    await dataset.uploadDataset(form)
    expect(send.mock.calls[1]?.[0]).toMatchObject({ data: form })
  })
  it('API Promise 与 Schema 输入通过编译期检查', () => {
    expectTypeOf(problem.getProblemDetail).returns.toEqualTypeOf<Promise<ProblemDetailResponse>>()
    expectTypeOf(problem.downloadTestCases).returns.toEqualTypeOf<Promise<Blob>>()
    expectTypeOf<LoginInput>().toEqualTypeOf<{ username: string; password: string }>()
    expectTypeOf(problem.submitSolution).parameter(0).toEqualTypeOf<SubmitCodeBody | FormData>()
    expectTypeOf(debug.debugSolution).parameter(0).toEqualTypeOf<{
      problem_id: number
      code: string
      language: string
      exam_id?: number | null
    }>()
    expectTypeOf(llm.askLLM).parameter(0).toExtend<{ system_setting: string; prompt: string }>()
  })
})
