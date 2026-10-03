"""LLM HTTP 接口：同步/流式问答、AI 草稿箱（异步任务）。"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import JsonValue

from app.api.auth_context import AuthContext, get_current_auth
from app.api.deps import get_ai_draft_service, get_llm_facade_service
from app.api.schemas.ai_draft import (
    ApplyDraftResponse,
    AskLlmBody,
    AskLlmSSEBody,
    DraftDetailResponse,
    DraftListResponse,
    DraftStatsResponse,
    ExecuteGenerationResponse,
    ExecuteTestDataDraftBody,
    ExecuteTestGenerationBody,
    GenerateProblemDraftBody,
    GenerateTestScriptDraftBody,
    SubmitDraftResponse,
)
from app.api.schemas.common import MessageResponse
from app.services.ai_draft import (
    AiDraftService,
    SubmitProblemGenerationParams,
    SubmitTestDataExecutionParams,
    SubmitTestScriptGenerationParams,
)
from app.services.llm import AskLlmParams, LlmFacadeService

router = APIRouter()


def _dt_iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat()


# ---------------------------------------------------------------------------
# 同步/流式 AI 问答
# ---------------------------------------------------------------------------


@router.post("/ask", response_model=dict[str, JsonValue])
def call_llm(
    body: AskLlmBody,
    auth: AuthContext = Depends(get_current_auth),
    service: LlmFacadeService = Depends(get_llm_facade_service),
):
    return service.ask(
        AskLlmParams(
            system_setting=body.system_setting,
            requester_role=auth.user.role,
            prompt=body.prompt,
            output_format=body.output_format,
            context_submission_id=body.context_submission_id,
        )
    ).payload


@router.post("/ask/stream", response_model=None)
def call_llm_stream(
    body: AskLlmSSEBody,
    auth: AuthContext = Depends(get_current_auth),
    service: LlmFacadeService = Depends(get_llm_facade_service),
):
    """
    SSE 流式 AI 答疑端点。

    SSE 事件格式：
      event: text   data: <token>     （每个 token）
      event: done   data:             （结束时）
      event: error  data: <错误信息>  （出错时）
    """
    params = AskLlmParams(
        system_setting=body.system_setting,
        requester_role=auth.user.role,
        prompt=body.prompt,
        output_format=body.output_format,
        context_submission_id=body.context_submission_id,
    )
    return StreamingResponse(
        service.ask_stream(params),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# 异步 AI 草稿箱（按分层规范新增）
# ---------------------------------------------------------------------------


@router.post(
    "/drafts/problem-generation", status_code=202, response_model=SubmitDraftResponse
)
def submit_problem_generation(
    body: GenerateProblemDraftBody,
    auth: AuthContext = Depends(get_current_auth),
    service: AiDraftService = Depends(get_ai_draft_service),
):
    """异步 AI 出题：立即返回草稿 ID，结果写入草稿箱。"""
    result = service.submit_problem_generation(
        SubmitProblemGenerationParams(
            user_id=auth.user.id,
            requester_role=auth.user.role,
            background=body.background,
            difficulty=body.difficulty,
        )
    )

    return {
        "draft_id": result.draft_id,
        "status": result.status,
        "task_type": result.task_type,
        "title": result.title,
        "message": "任务已提交，请到草稿箱查看进度",
    }


@router.post(
    "/drafts/test-script-generation",
    status_code=202,
    response_model=SubmitDraftResponse,
)
def submit_test_script_generation(
    body: GenerateTestScriptDraftBody,
    auth: AuthContext = Depends(get_current_auth),
    service: AiDraftService = Depends(get_ai_draft_service),
):
    """异步生成测例/评估脚本。"""
    result = service.submit_test_script_generation(
        SubmitTestScriptGenerationParams(
            user_id=auth.user.id,
            requester_role=auth.user.role,
            problem_id=body.problem_id,
            direction=body.direction,
        )
    )

    return {
        "draft_id": result.draft_id,
        "status": result.status,
        "task_type": result.task_type,
        "title": result.title,
        "message": "任务已提交，请到草稿箱查看进度",
    }


@router.post(
    "/drafts/test-data-execution", status_code=202, response_model=SubmitDraftResponse
)
def submit_test_data_execution(
    body: ExecuteTestDataDraftBody,
    auth: AuthContext = Depends(get_current_auth),
    service: AiDraftService = Depends(get_ai_draft_service),
):
    """异步执行测例生成或保存非 ACM 脚本。"""
    result = service.submit_test_data_execution(
        SubmitTestDataExecutionParams(
            user_id=auth.user.id,
            requester_role=auth.user.role,
            problem_id=body.problem_id,
            code=body.code,
            problem_type=body.type,
            language=body.language,
            source_draft_id=body.source_draft_id,
        )
    )

    return {
        "draft_id": result.draft_id,
        "status": result.status,
        "task_type": result.task_type,
        "title": result.title,
        "message": "任务已提交，请到草稿箱查看进度",
    }


# ---------------------------------------------------------------------------
# 兼容：旧接口（将请求投递到 Judge Worker）
# ---------------------------------------------------------------------------


@router.post(
    "/execute-test-generation",
    status_code=202,
    response_model=ExecuteGenerationResponse,
)
def execute_test_generation(
    body: ExecuteTestGenerationBody,
    auth: AuthContext = Depends(get_current_auth),
    service: AiDraftService = Depends(get_ai_draft_service),
):
    """兼容旧接口。"""
    result = service.submit_test_data_execution(
        SubmitTestDataExecutionParams(
            user_id=auth.user.id,
            requester_role=auth.user.role,
            problem_id=body.problem_id,
            code=body.code,
            problem_type=body.type or "acm",
            language=body.language,
        )
    )
    return {
        "message": "测试数据执行任务已提交，请到草稿箱查看进度",
        "draft_id": result.draft_id,
        "status": result.status,
    }


# ---------------------------------------------------------------------------
# 草稿箱查询与操作
# ---------------------------------------------------------------------------


@router.get("/drafts", response_model=DraftListResponse)
def list_drafts(
    status: Optional[str] = Query(default=None),
    task_type: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    auth: AuthContext = Depends(get_current_auth),
    service: AiDraftService = Depends(get_ai_draft_service),
):
    """列出当前教师的草稿箱任务。"""
    items = service.list_drafts(
        auth.user.id,
        status=status,
        task_type=task_type,
        limit=limit,
        requester_role=auth.user.role,
    )

    return {
        "drafts": [
            {
                "id": item.id,
                "task_type": item.task_type,
                "status": item.status,
                "title": item.title,
                "problem_id": item.problem_id,
                "error_message": item.error_message,
                "created_at": _dt_iso(item.created_at),
                "updated_at": _dt_iso(item.updated_at),
                "consumed_at": _dt_iso(item.consumed_at),
            }
            for item in items
        ]
    }


@router.get("/drafts/stats", response_model=DraftStatsResponse)
def draft_stats(
    auth: AuthContext = Depends(get_current_auth),
    service: AiDraftService = Depends(get_ai_draft_service),
):
    """草稿箱统计（角标用）。"""
    stats = service.get_stats(auth.user.id, requester_role=auth.user.role)

    return {
        "total": stats.total,
        "pending": stats.pending,
        "running": stats.running,
        "success": stats.success,
        "failed": stats.failed,
        "unconsumed_success": stats.unconsumed_success,
        "in_progress": stats.pending + stats.running,
    }


@router.get("/drafts/{draft_id}", response_model=DraftDetailResponse)
def get_draft(
    draft_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: AiDraftService = Depends(get_ai_draft_service),
):
    """草稿详情。"""
    item = service.get_draft(auth.user.id, draft_id, requester_role=auth.user.role)

    return {
        "id": item.id,
        "task_type": item.task_type,
        "status": item.status,
        "title": item.title,
        "problem_id": item.problem_id,
        "request_payload": item.request_payload,
        "result_payload": item.result_payload,
        "error_message": item.error_message,
        "created_at": _dt_iso(item.created_at),
        "updated_at": _dt_iso(item.updated_at),
        "consumed_at": _dt_iso(item.consumed_at),
    }


@router.delete("/drafts/{draft_id}", response_model=MessageResponse)
def delete_draft(
    draft_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: AiDraftService = Depends(get_ai_draft_service),
):
    """删除草稿。"""
    service.delete_draft(auth.user.id, draft_id, requester_role=auth.user.role)
    return {"message": "草稿已删除"}


@router.post("/drafts/{draft_id}/apply", response_model=ApplyDraftResponse)
def apply_problem_draft(
    draft_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: AiDraftService = Depends(get_ai_draft_service),
):
    """将成功的出题草稿创建为正式题目。"""
    result = service.apply_problem_draft(
        auth.user.id, draft_id, requester_role=auth.user.role
    )

    return {
        "message": "题目创建成功",
        "problem_id": result.problem_id,
        "draft_id": result.draft_id,
        "title": result.title,
    }
