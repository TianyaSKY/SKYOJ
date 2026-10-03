"""ACM 调试运行 API。

- POST /api/debug 提交调试代码：仅学生角色可用，仅 ACM 题目可用；异步执行、不入 `submissions`。
- GET  /api/debug/{debug_run_id} 查询调试结果：仅本人或非学生可查看。
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import ValidationError

from app.api.auth_context import AuthContext, get_current_auth
from app.api.deps import get_debug_service
from app.api.schemas.debug import DebugCodeBody
from app.api.schemas.debug_run import CreateDebugRunResponse, DebugRunResponse
from app.services.debug import CreateDebugRunParams, DebugService

router = APIRouter()


@router.post("", status_code=202, response_model=CreateDebugRunResponse)
async def submit_debug(
    request: Request,
    auth: AuthContext = Depends(get_current_auth),
    service: DebugService = Depends(get_debug_service),
    problem_id: Optional[int] = Form(default=None),
    code: Optional[str] = Form(default=None),
    language: Optional[str] = Form(default=None),
    exam_id: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
):
    """接收调试请求；不写入 `submissions`，不计入考试或排行榜。"""

    content_type = request.headers.get("content-type", "")
    pid = problem_id
    user_code = None
    lang = language
    exam_id_val = -1

    if "application/json" in content_type:
        try:
            body = DebugCodeBody.model_validate(await request.json())
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
        pid = body.problem_id
        user_code = body.code
        lang = body.language
        exam_id_val = body.exam_id if body.exam_id is not None else -1
    else:
        pid = problem_id
        lang = language
        user_code = code or ""
        exam_id_val = exam_id if exam_id is not None else -1

        if file and file.filename:
            if lang == "csv" or file.filename.endswith(".csv"):
                raise HTTPException(
                    status_code=400,
                    detail={"error": "Debug does not accept CSV uploads."},
                )
            raw = await file.read()
            user_code = raw.decode("utf-8")

    if not pid or not user_code:
        raise HTTPException(
            status_code=400, detail={"error": "Missing problem_id or code/file"}
        )

    try:
        exam_id_val = int(exam_id_val)
    except (ValueError, TypeError):
        exam_id_val = -1

    try:
        validated = DebugCodeBody.model_validate(
            {
                "problem_id": pid,
                "code": user_code,
                "language": lang or "",
                "exam_id": exam_id_val,
            }
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    result = service.create(
        CreateDebugRunParams(
            user_id=auth.user.id,
            problem_id=validated.problem_id,
            language=validated.language,
            code=validated.code,
            exam_id=validated.exam_id,
        ),
        requester_role=auth.user.role,
    )

    return {
        "message": "Debug run received, running in background.",
        "debug_run_id": result.debug_run_id,
        "status": result.status,
        "exam_id": result.exam_id,
    }


@router.get("/{debug_run_id}", response_model=DebugRunResponse)
def get_debug_run(
    debug_run_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: DebugService = Depends(get_debug_service),
):
    detail = service.get_debug_run(debug_run_id, auth.user.id, auth.user.role)
    return {
        "id": detail.id,
        "status": detail.status,
        "language": detail.language,
        "case_name": detail.case_name,
        "input": detail.input,
        "expected_output": detail.expected_output,
        "actual_output": detail.actual_output,
        "error_output": detail.error_output,
        "time_used_ms": detail.time_used_ms,
        "memory_used_kb": detail.memory_used_kb,
        "created_at": detail.created_at.isoformat() if detail.created_at else None,
        "finished_at": detail.finished_at.isoformat() if detail.finished_at else None,
        "problem_id": detail.problem_id,
        "exam_id": detail.exam_id,
    }
