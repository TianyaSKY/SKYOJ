import os

from flask import Blueprint, jsonify, request

from app.services.judge_service import save_non_acm_script
from app.services.llm import ask_llm
from app.services.test_gen_service import run_test_generation
from app.utils.auth_tools import token_required

llm_bp = Blueprint('llm', __name__)


@llm_bp.route('/ask', methods=['POST'])
@token_required
def call_llm():
    """
    调用 LLM 接口，配置从环境变量中获取
    """
    data = request.get_json()
    system_setting = data.get('system_setting')
    prompt = data.get('prompt')
    output_format = data.get('output_format')

    if not system_setting or not prompt:
        return jsonify({"error": "system_setting and prompt are required"}), 400

    api_key = os.getenv('LLM_API_KEY', '').strip()
    api_url = os.getenv('LLM_API_URL', '').strip()
    model_name = os.getenv('LLM_MODEL_NAME', '').strip()

    if not all([api_key, api_url, model_name]):
        return jsonify({
            "error": "LLM environment variables are missing. Required: LLM_API_KEY, LLM_API_URL, LLM_MODEL_NAME"
        }), 500

    # 调用服务
    result = ask_llm(
        api_key=api_key,
        api_url=api_url,
        model_name=model_name,
        system_setting=system_setting,
        prompt=prompt,
        output_format=output_format
    )

    if result is None:
        return jsonify({"error": "LLM request failed or output format mismatch"}), 500

    return jsonify(result), 200


@llm_bp.route('/execute-test-generation', methods=['POST'])
@token_required
def execute_test_generation():
    """
    执行 LLM 生成的测试数据脚本并保存结果
    """
    data = request.get_json()
    problem_id = data.get('problem_id')
    code = data.get('code')
    problem_type = data.get('type')
    language = data.get('language', 'python')

    if not problem_id or not code:
        return jsonify({"error": "problem_id and code are required"}), 400

    # 如果不是 ACM 类型，直接保存代码文件
    if problem_type and problem_type != 'acm':
        success, message = save_non_acm_script(problem_id, code, problem_type, language)
        if success:
            return jsonify({"message": message}), 200
        else:
            return jsonify({"error": message}), 500

    # ACM 类型则运行脚本生成数据
    success, message = run_test_generation(problem_id, code)

    if success:
        return jsonify({"message": message}), 200
    else:
        return jsonify({"error": message}), 500
