import request from '@/utils/request'

/**
 * 统一 LLM 对话接口
 * @param {Object} data { system_setting, prompt, output_format, ... }
 */
export function askLLM(data) {
    return request({
        url: '/llm/ask',
        method: 'post',
        data,
        timeout: 300000 // LLM 接口响应较慢，单独设置超时
    })
}

/**
 * 执行生成的脚本/类以生成并提交测试数据
 * @param {Object} data { problem_id, code, type: 'python' | 'java' }
 */
export function executeAndSubmitTestData(data) {
    return request({
        url: '/llm/execute-test-generation',
        method: 'post',
        data,
        timeout: 120000 // 生成数据并提交可能需要更长时间
    })
}
