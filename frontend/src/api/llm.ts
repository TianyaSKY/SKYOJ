import type * as AiDraft from '@/types/aiDraft'
import type { GenerateProblemDraftInput, GenerateTestScriptDraftInput, ExecuteTestDataDraftInput } from '@/schemas/aiDraft'
import type { MessageResponse, JsonValue } from '@/types/common'
import request from '@/utils/request'

/**
 * 统一 LLM 对话接口（同步，保留兼容）
 * @param {Object} data { system_setting, prompt, output_format, ... }
 */
export function askLLM(data: AiDraft.AskLlmBody): Promise<Record<string, JsonValue>> {
    return request<Record<string, JsonValue>>({
        url: '/llm/ask',
        method: 'post',
        data,
        timeout: 300000
    })
}

/**
 * 执行生成的脚本/类以生成并提交测试数据（兼容接口，后台异步执行）
 * @param {Object} data { problem_id, code, type, language }
 */
export function executeAndSubmitTestData(data: AiDraft.ExecuteTestGenerationBody): Promise<AiDraft.ExecuteGenerationResponse> {
    return request<AiDraft.ExecuteGenerationResponse>({
        url: '/llm/execute-test-generation',
        method: 'post',
        data,
        timeout: 120000
    })
}

/** 异步 AI 出题 */
export function submitProblemGenerationDraft(data: GenerateProblemDraftInput): Promise<AiDraft.SubmitDraftResponse> {
    return request<AiDraft.SubmitDraftResponse>({
        url: '/llm/drafts/problem-generation',
        method: 'post',
        data,
        timeout: 30000
    })
}

/** 异步生成测例脚本 */
export function submitTestScriptGenerationDraft(data: GenerateTestScriptDraftInput): Promise<AiDraft.SubmitDraftResponse> {
    return request<AiDraft.SubmitDraftResponse>({
        url: '/llm/drafts/test-script-generation',
        method: 'post',
        data,
        timeout: 30000
    })
}

/** 异步执行测例 / 保存脚本 */
export function submitTestDataExecutionDraft(data: ExecuteTestDataDraftInput): Promise<AiDraft.SubmitDraftResponse> {
    return request<AiDraft.SubmitDraftResponse>({
        url: '/llm/drafts/test-data-execution',
        method: 'post',
        data,
        timeout: 30000
    })
}

/** 草稿列表 */
export function listAiDrafts(params?: AiDraft.DraftQuery): Promise<AiDraft.DraftListResponse> {
    return request<AiDraft.DraftListResponse>({
        url: '/llm/drafts',
        method: 'get',
        params
    })
}

/** 草稿统计 */
export function getAiDraftStats(): Promise<AiDraft.DraftStatsResponse> {
    return request<AiDraft.DraftStatsResponse>({
        url: '/llm/drafts/stats',
        method: 'get'
    })
}

/** 草稿详情 */
export function getAiDraftDetail(id: number): Promise<AiDraft.DraftDetailResponse> {
    return request<AiDraft.DraftDetailResponse>({
        url: `/llm/drafts/${id}`,
        method: 'get'
    })
}

/** 删除草稿 */
export function deleteAiDraft(id: number): Promise<MessageResponse> {
    return request<MessageResponse>({
        url: `/llm/drafts/${id}`,
        method: 'delete'
    })
}

/** 应用出题草稿为正式题目 */
export function applyProblemDraft(id: number): Promise<AiDraft.ApplyDraftResponse> {
    return request<AiDraft.ApplyDraftResponse>({
        url: `/llm/drafts/${id}/apply`,
        method: 'post'
    })
}
