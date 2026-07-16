"""LLM 外部 API 客户端。"""

import json
import os
from typing import Any, Optional

from loguru import logger


class LlmClient:
    """封装 OpenAI 兼容接口的调用。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        self._api_key = (api_key if api_key is not None else os.getenv("LLM_API_KEY", "")).strip()
        self._api_url = (api_url if api_url is not None else os.getenv("LLM_API_URL", "")).strip()
        self._model_name = (
            model_name if model_name is not None else os.getenv("LLM_MODEL_NAME", "")
        ).strip()

    def is_configured(self) -> bool:
        """是否已配置完整 LLM 环境变量。"""
        return bool(self._api_key and self._api_url and self._model_name)

    def chat_json(
        self,
        *,
        system_setting: str,
        prompt: str,
        output_format: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        调用 LLM 并解析 JSON 结果。

        失败时抛出 RuntimeError，由上层映射为业务异常。
        """
        if not self.is_configured():
            raise RuntimeError(
                "LLM environment variables are missing. "
                "Required: LLM_API_KEY, LLM_API_URL, LLM_MODEL_NAME"
            )

        from openai import OpenAI

        full_system_prompt = system_setting
        if output_format:
            full_system_prompt += (
                "\n\n请务必仅以 JSON 格式返回结果，格式如下：\n"
                f"{json.dumps(output_format, ensure_ascii=False, indent=2)}"
            )

        client = OpenAI(api_key=self._api_key, base_url=self._api_url)
        kwargs: dict[str, Any] = {
            "model": self._model_name,
            "messages": [
                {"role": "system", "content": full_system_prompt},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }

        if "deepseek" in self._model_name.lower():
            kwargs["extra_body"] = {"enable_thinking": False}

        if output_format:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            parsed = json.loads(content)
        except Exception as exc:
            logger.error("LLM 请求失败: {}", str(exc))
            raise RuntimeError(f"LLM 请求失败: {exc}") from exc

        if output_format:
            for key in output_format.keys():
                if key not in parsed:
                    logger.error("LLM 返回格式不匹配: 缺失键 {}", key)
                    raise RuntimeError(f"LLM 返回格式不匹配: 缺失键 {key}")

        return parsed
