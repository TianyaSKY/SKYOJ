import json
from typing import Optional, Dict, Any
from openai import OpenAI

def ask_llm(
    api_key: str,
    api_url: str,
    model_name: str,
    system_setting: str,
    prompt: str,
    output_format: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    基于 OpenAI SDK 向 LLM 发送请求并获取 JSON 返回信息。
    支持 DeepSeek 等模型的推理过程 (reasoning_content) 过滤，仅返回最终结果。
    """
    
    # 构造系统提示词，包含输出格式要求
    full_system_prompt = system_setting
    if output_format:
        full_system_prompt += f"\n\n请务必仅以 JSON 格式返回结果，格式如下：\n{json.dumps(output_format, ensure_ascii=False, indent=2)}"

    # 初始化 OpenAI 客户端
    client = OpenAI(
        api_key=api_key,
        base_url=api_url
    )

    try:
        # 构造请求参数
        kwargs = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": full_system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False  # API 接口通常不需要流式返回给前端
        }

        # 如果是 DeepSeek 等支持推理的模型，可以尝试开启 thinking (根据具体 API 供应商支持情况)
        # 这里默认不开启 extra_body 以保持通用性，如果需要可以根据 model_name 判断添加
        if "deepseek" in model_name.lower():
            kwargs["extra_body"] = {"enable_thinking": False}

        # 如果指定了输出格式，强制要求返回 JSON
        if output_format:
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)
        
        # 获取最终回答内容
        content = response.choices[0].message.content
        
        # 解析返回的 JSON 内容
        parsed_content = json.loads(content)
        
        # 如果指定了 output_format，检查返回的 key 是否匹配
        if output_format:
            for key in output_format.keys():
                if key not in parsed_content:
                    print(f"LLM 返回格式不匹配: 缺失键 {key}")
                    return None
                    
        return parsed_content

    except Exception as e:
        print(f"LLM 请求失败: {str(e)}")
        return None
