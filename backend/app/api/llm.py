import os
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.services.judge_service import save_non_acm_script
from app.services.llm import ask_llm
from app.services.test_gen_service import run_test_generation
from app.utils.auth_tools import AuthContext, get_current_auth

router = APIRouter()


@router.post("/ask")
def call_llm(
    data: dict[str, Any],
    auth: AuthContext = Depends(get_current_auth),
):
    system_setting = data.get("system_setting")
    prompt = data.get("prompt")
    output_format = data.get("output_format")

    if not system_setting or not prompt:
        raise HTTPException(
            status_code=400,
            detail={"error": "system_setting and prompt are required"},
        )

    api_key = os.getenv("LLM_API_KEY", "").strip()
    api_url = os.getenv("LLM_API_URL", "").strip()
    model_name = os.getenv("LLM_MODEL_NAME", "").strip()

    if not all([api_key, api_url, model_name]):
        raise HTTPException(
            status_code=500,
            detail={
                "error": "LLM environment variables are missing. Required: LLM_API_KEY, LLM_API_URL, LLM_MODEL_NAME"
            },
        )

    result = ask_llm(
        api_key=api_key,
        api_url=api_url,
        model_name=model_name,
        system_setting=system_setting,
        prompt=prompt,
        output_format=output_format,
    )
    if result is None:
        raise HTTPException(
            status_code=500,
            detail={"error": "LLM request failed or output format mismatch"},
        )
    return result


@router.post("/execute-test-generation")
def execute_test_generation(
    data: dict[str, Any],
    auth: AuthContext = Depends(get_current_auth),
):
    problem_id = data.get("problem_id")
    code = data.get("code")
    problem_type = data.get("type")
    language = data.get("language", "python")

    if not problem_id or not code:
        raise HTTPException(
            status_code=400, detail={"error": "problem_id and code are required"}
        )

    if problem_type and problem_type != "acm":
        success, message = save_non_acm_script(
            problem_id, code, problem_type, language
        )
        if success:
            return {"message": message}
        raise HTTPException(status_code=500, detail={"error": message})

    success, message = run_test_generation(problem_id, code)
    if success:
        return {"message": message}
    raise HTTPException(status_code=500, detail={"error": message})
