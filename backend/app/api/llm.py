from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_ai_draft_service, get_llm_facade_service
from app.api.schemas.ai_draft import (
    ExecuteTestDataDraftBody,
    ExecuteTestGenerationBody,
    GenerateProblemDraftBody,
    GenerateTestScriptDraftBody,
    AskLlmBody,
)
from app.domain.ai_draft import (
    SubmitProblemGenerationParams,
    SubmitTestDataExecutionParams,
    SubmitTestScriptGenerationParams,
)
from app.domain.errors import (
    BusinessError,
    ExternalServiceError,
    InvalidStateError,
    LlmConfigError,
    PermissionDeniedError,
    ResourceNotFoundError,
)
from app.domain.llm import AskLlmParams, ExecuteTestGenerationParams
from app.services.ai_draft_service import AiDraftService
from app.services.llm_facade_service import LlmFacadeService
from app.utils.auth_tools import AuthContext, get_current_auth

router = APIRouter()


def _require_teacher(auth: AuthContext) -> None:
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})


def _map_business_error(exc: BusinessError) -> HTTPException:
    """将业务异常映射为 HTTP 响应。"""
    if isinstance(exc, ResourceNotFoundError):
        return HTTPException(status_code=404, detail={"error": str(exc)})
    if isinstance(exc, PermissionDeniedError):
        return HTTPException(status_code=403, detail={"error": str(exc)})
    if isinstance(exc, (InvalidStateError, LlmConfigError)):
        return HTTPException(status_code=400, detail={"error": str(exc)})
    if isinstance(exc, ExternalServiceError):
        return HTTPException(status_code=502, detail={"error": str(exc)})
    return HTTPException(status_code=400, detail={"error": str(exc)})


def _dt_iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat()


# ---------------------------------------------------------------------------
# 兼容：同步接口（历史行为保留，后续可再分层改造）
# ---------------------------------------------------------------------------


@router.post("/ask")
def call_llm(
    body: AskLlmBody,
    auth: AuthContext = Depends(get_current_auth),
    service: LlmFacadeService = Depends(get_llm_facade_service),
):
    try:
        return service.ask(AskLlmParams(body.system_setting, body.prompt, body.output_format))
    except BusinessError as exc:
        raise _map_business_error(exc) from exc


@router.post("/execute-test-generation")
def execute_test_generation(
    body: ExecuteTestGenerationBody,
    auth: AuthContext = Depends(get_current_auth),
    service: LlmFacadeService = Depends(get_llm_facade_service),
):
    try:
        message = service.execute_test_generation(
            ExecuteTestGenerationParams(
                body.problem_id, body.code, body.type, body.language
            )
        )
    except BusinessError as exc:
        raise _map_business_error(exc) from exc
    return {"message": message}


# ---------------------------------------------------------------------------
# 异步草稿箱接口（按分层规范新增）
# ---------------------------------------------------------------------------


@router.post("/drafts/problem-generation", status_code=202)
def submit_problem_generation(
    body: GenerateProblemDraftBody,
    auth: AuthContext = Depends(get_current_auth),
    service: AiDraftService = Depends(get_ai_draft_service),
):
    """异步 AI 出题：立即返回草稿 ID，结果写入草稿箱。"""
    _require_teacher(auth)
    try:
        result = service.submit_problem_generation(
            SubmitProblemGenerationParams(
                user_id=auth.user.id,
                background=body.background,
                difficulty=body.difficulty,
            )
        )
    except BusinessError as exc:
        raise _map_business_error(exc) from exc

    return {
        "draft_id": result.draft_id,
        "status": result.status,
        "task_type": result.task_type,
        "title": result.title,
        "message": "任务已提交，请到草稿箱查看进度",
    }


@router.post("/drafts/test-script-generation", status_code=202)
def submit_test_script_generation(
    body: GenerateTestScriptDraftBody,
    auth: AuthContext = Depends(get_current_auth),
    service: AiDraftService = Depends(get_ai_draft_service),
):
    """异步生成测例/评估脚本。"""
    _require_teacher(auth)
    try:
        result = service.submit_test_script_generation(
            SubmitTestScriptGenerationParams(
                user_id=auth.user.id,
                problem_id=body.problem_id,
                direction=body.direction,
            )
        )
    except BusinessError as exc:
        raise _map_business_error(exc) from exc

    return {
        "draft_id": result.draft_id,
        "status": result.status,
        "task_type": result.task_type,
        "title": result.title,
        "message": "任务已提交，请到草稿箱查看进度",
    }


@router.post("/drafts/test-data-execution", status_code=202)
def submit_test_data_execution(
    body: ExecuteTestDataDraftBody,
    auth: AuthContext = Depends(get_current_auth),
    service: AiDraftService = Depends(get_ai_draft_service),
):
    """异步执行测例生成或保存非 ACM 脚本。"""
    _require_teacher(auth)
    try:
        result = service.submit_test_data_execution(
            SubmitTestDataExecutionParams(
                user_id=auth.user.id,
                problem_id=body.problem_id,
                code=body.code,
                problem_type=body.type,
                language=body.language,
                source_draft_id=body.source_draft_id,
            )
        )
    except BusinessError as exc:
        raise _map_business_error(exc) from exc

    return {
        "draft_id": result.draft_id,
        "status": result.status,
        "task_type": result.task_type,
        "title": result.title,
        "message": "任务已提交，请到草稿箱查看进度",
    }


@router.get("/drafts")
def list_drafts(
    status: Optional[str] = Query(default=None),
    task_type: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    auth: AuthContext = Depends(get_current_auth),
    service: AiDraftService = Depends(get_ai_draft_service),
):
    """列出当前教师的草稿箱任务。"""
    _require_teacher(auth)
    try:
        items = service.list_drafts(
            auth.user.id,
            status=status,
            task_type=task_type,
            limit=limit,
        )
    except BusinessError as exc:
        raise _map_business_error(exc) from exc

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


@router.get("/drafts/stats")
def draft_stats(
    auth: AuthContext = Depends(get_current_auth),
    service: AiDraftService = Depends(get_ai_draft_service),
):
    """草稿箱统计（角标用）。"""
    _require_teacher(auth)
    try:
        stats = service.get_stats(auth.user.id)
    except BusinessError as exc:
        raise _map_business_error(exc) from exc

    return {
        "total": stats.total,
        "pending": stats.pending,
        "running": stats.running,
        "success": stats.success,
        "failed": stats.failed,
        "unconsumed_success": stats.unconsumed_success,
        "in_progress": stats.pending + stats.running,
    }


@router.get("/drafts/{draft_id}")
def get_draft(
    draft_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: AiDraftService = Depends(get_ai_draft_service),
):
    """草稿详情。"""
    _require_teacher(auth)
    try:
        item = service.get_draft(auth.user.id, draft_id)
    except BusinessError as exc:
        raise _map_business_error(exc) from exc

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


@router.delete("/drafts/{draft_id}")
def delete_draft(
    draft_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: AiDraftService = Depends(get_ai_draft_service),
):
    """删除草稿。"""
    _require_teacher(auth)
    try:
        service.delete_draft(auth.user.id, draft_id)
    except BusinessError as exc:
        raise _map_business_error(exc) from exc
    return {"message": "草稿已删除"}


@router.post("/drafts/{draft_id}/apply")
def apply_problem_draft(
    draft_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: AiDraftService = Depends(get_ai_draft_service),
):
    """将成功的出题草稿创建为正式题目。"""
    _require_teacher(auth)
    try:
        result = service.apply_problem_draft(auth.user.id, draft_id)
    except BusinessError as exc:
        raise _map_business_error(exc) from exc

    return {
        "message": "题目创建成功",
        "problem_id": result.problem_id,
        "draft_id": result.draft_id,
        "title": result.title,
    }
