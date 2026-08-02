import request from '@/utils/request'

/**
 * 统一 LLM 对话接口（同步，保留兼容）
 * @param {Object} data { system_setting, prompt, output_format, ... }
 */
export function askLLM(data) {
    return request({
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
export function executeAndSubmitTestData(data) {
    return request({
        url: '/llm/execute-test-generation',
        method: 'post',
        data,
        timeout: 120000
    })
}

/** 异步 AI 出题 */
export function submitProblemGenerationDraft(data) {
    return request({
        url: '/llm/drafts/problem-generation',
        method: 'post',
        data,
        timeout: 30000
    })
}

/** 异步生成测例脚本 */
export function submitTestScriptGenerationDraft(data) {
    return request({
        url: '/llm/drafts/test-script-generation',
        method: 'post',
        data,
        timeout: 30000
    })
}

/** 异步执行测例 / 保存脚本 */
export function submitTestDataExecutionDraft(data) {
    return request({
        url: '/llm/drafts/test-data-execution',
        method: 'post',
        data,
        timeout: 30000
    })
}

/** 草稿列表 */
export function listAiDrafts(params) {
    return request({
        url: '/llm/drafts',
        method: 'get',
        params
    })
}

/** 草稿统计 */
export function getAiDraftStats() {
    return request({
        url: '/llm/drafts/stats',
        method: 'get'
    })
}

/** 草稿详情 */
export function getAiDraftDetail(id) {
    return request({
        url: `/llm/drafts/${id}`,
        method: 'get'
    })
}

/** 删除草稿 */
export function deleteAiDraft(id) {
    return request({
        url: `/llm/drafts/${id}`,
        method: 'delete'
    })
}

/** 应用出题草稿为正式题目 */
export function applyProblemDraft(id) {
    return request({
        url: `/llm/drafts/${id}/apply`,
        method: 'post'
    })
}
