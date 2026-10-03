from typing import Optional

import anyio
from redis import RedisError
from starlette.concurrency import run_in_threadpool

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from loguru import logger
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.auth_context import AuthContext, get_current_auth
from app.api.deps import get_submission_service
from app.api.schemas.submission import (
    PaginatedSubmissionsResponse,
    SubmissionDetailResponse,
    SubmitCodeBody,
    SubmitCodeResponse,
)
from app.clients.redis_client import redis_client
from app.core.errors import PermissionDeniedError, ResourceNotFoundError
from app.persistence.database import get_db
from app.middleware.rate_limit import enforce
from app.services.submission import SubmissionDetail, SubmissionQuery, SubmissionService, SubmitParams

router = APIRouter()


@router.websocket("/ws/{submission_id}")
async def submission_websocket(
    ws: WebSocket,
    submission_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
    service: SubmissionService = Depends(get_submission_service),
):
    """实时推送提交判题结果。

    鉴权：token 放在 query 参数中，按当前用户身份校验提交归属；教师可订阅全部提交。
    推送消息：{"status": "...", "score": 100.0, "output_log": "..."}
    """
    try:
        auth = await run_in_threadpool(get_current_auth, authorization=token, db=db)
    except HTTPException:
        await ws.close(code=4001, reason="Invalid token")
        return

    try:
        detail = await run_in_threadpool(service.get_submission, submission_id, auth.user.id, auth.user.role)
    except PermissionDeniedError:
        await ws.close(code=4003, reason="Forbidden")
        return
    except ResourceNotFoundError:
        await ws.close(code=4004, reason="Submission not found")
        return

    pubsub = None

    async def send_completed(snapshot: SubmissionDetail) -> bool:
        if snapshot.status in {"Pending", "Judging", "Compiling"}:
            return False
        await ws.send_json({
            "submission_id": submission_id,
            "status": snapshot.status,
            "score": snapshot.score,
            "output_log": snapshot.log or "",
        })
        await ws.close(code=1000, reason="Result delivered")
        return True

    def refresh_result() -> SubmissionDetail:
        # 此连接只读；结束旧事务，避免身份映射或 MySQL 快照缓存旧的 Pending 状态。
        db.rollback()
        return service.get_submission(submission_id, auth.user.id, auth.user.role)

    try:
        await ws.accept()
        if await send_completed(detail):
            return
        client = await run_in_threadpool(redis_client.get_client)
        if client is None:
            await ws.close(code=1011, reason="Redis not available")
            return
        pubsub = await run_in_threadpool(client.pubsub)
        await run_in_threadpool(pubsub.subscribe, f"skyoj:submission:{submission_id}")
        # 订阅建立期间可能已经完成判题，数据库是最终结果的权威来源。
        if await send_completed(await run_in_threadpool(refresh_result)):
            return

        async with anyio.create_task_group() as tasks:
            async def watch_disconnect():
                # 无消息时也能及时停止订阅，不等待下一次判题推送。
                while True:
                    event = await ws.receive()
                    if event["type"] == "websocket.disconnect":
                        tasks.cancel_scope.cancel()
                        return

            tasks.start_soon(watch_disconnect)
            try:
                with anyio.move_on_after(300) as timeout:
                    while True:
                        msg = await run_in_threadpool(
                            pubsub.get_message, timeout=1.0, ignore_subscribe_messages=True
                        )
                        if msg and msg["type"] == "message":
                            await ws.send_text(msg["data"])
                            break
                        if msg is None and await send_completed(await run_in_threadpool(refresh_result)):
                            return
                await ws.close(
                    code=1000,
                    reason="Subscription timed out" if timeout.cancel_called else "Result delivered",
                )
            except RedisError:
                logger.exception("读取提交订阅失败 submission_id={}", submission_id)
                await ws.close(code=1011, reason="Redis not available")
            except ResourceNotFoundError:
                await ws.close(code=4004, reason="Submission not found")
            except WebSocketDisconnect:
                pass
            finally:
                tasks.cancel_scope.cancel()
    except RedisError:
        logger.exception("建立提交订阅失败 submission_id={}", submission_id)
        await ws.close(code=1011, reason="Redis not available")
    except ResourceNotFoundError:
        await ws.close(code=4004, reason="Submission not found")
    except WebSocketDisconnect:
        pass
    finally:
        if pubsub is not None:
            # 任务取消时仍完成清理；取消订阅失败不能阻止连接关闭。
            with anyio.CancelScope(shield=True):
                try:
                    await run_in_threadpool(pubsub.unsubscribe)
                except Exception:
                    logger.exception("取消提交订阅失败 submission_id={}", submission_id)
                try:
                    await run_in_threadpool(pubsub.close)
                except Exception:
                    logger.exception("关闭提交订阅失败 submission_id={}", submission_id)


@router.post("/submit", status_code=202, response_model=SubmitCodeResponse)
async def submit_code(
    request: Request,
    auth: AuthContext = Depends(get_current_auth),
    service: SubmissionService = Depends(get_submission_service),
    problem_id: Optional[int] = Form(default=None),
    code: Optional[str] = Form(default=None),
    language: Optional[str] = Form(default=None),
    exam_id: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
):
    enforce(f"submit:{auth.user.id}", limit=10, window_seconds=60)

    content_type = request.headers.get("content-type", "")
    user_code = None
    exam_id_val = -1
    lang = language
    pid = problem_id

    if "application/json" in content_type:
        try:
            body = SubmitCodeBody.model_validate(await request.json())
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
                content = await file.read()
                user_code = "__file_upload__"
            else:
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
        validated = SubmitCodeBody.model_validate(
            {
                "problem_id": pid,
                "code": user_code,
                "language": lang or "",
                "exam_id": exam_id_val,
            }
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    result = service.submit(
        SubmitParams(
            user_id=auth.user.id,
            problem_id=validated.problem_id,
            code=validated.code,
            language=validated.language,
            exam_id=validated.exam_id,
            session_exam_id=auth.exam_id,
            is_file_upload=bool(
                file
                and file.filename
                and (lang == "csv" or file.filename.endswith(".csv"))
            ),
            filename=file.filename if file else None,
            file_content=content
            if file
            and file.filename
            and (lang == "csv" or file.filename.endswith(".csv"))
            else None,
        ),
        requester_role=auth.user.role,
    )

    return {
        "message": "Submission received, judging in background.",
        "submission_id": result.submission_id,
        "status": result.status,
        "exam_id": result.exam_id,
    }


@router.get("", response_model=PaginatedSubmissionsResponse)
def list_submissions(
    problem_id: Optional[int] = None,
    user_id: Optional[int] = None,
    exam_id: Optional[int] = None,
    status: Optional[str] = None,
    username: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    auth: AuthContext = Depends(get_current_auth),
    service: SubmissionService = Depends(get_submission_service),
):
    result = service.list_submissions(
        SubmissionQuery(
            requester_id=auth.user.id,
            requester_role=auth.user.role,
            problem_id=problem_id,
            user_id=user_id,
            exam_id=exam_id,
            status=status,
            username=username,
            page=page,
            page_size=per_page,
        )
    )

    return {
        "total": result.total,
        "pages": result.pages,
        "current_page": result.current_page,
        "submissions": [
            {
                "id": s.id,
                "user_id": s.user_id,
                "username": s.username,
                "problem_id": s.problem_id,
                "exam_id": s.exam_id,
                "status": s.status,
                "score": s.score,
                "language": s.language,
                "created_at": s.created_at.isoformat(),
            }
            for s in result.submissions
        ],
    }


@router.get("/{submission_id}", response_model=SubmissionDetailResponse)
def get_submission(
    submission_id: int,
    auth: AuthContext = Depends(get_current_auth),
    service: SubmissionService = Depends(get_submission_service),
):
    submission = service.get_submission(submission_id, auth.user.id, auth.user.role)

    return {
        "id": submission.id,
        "status": submission.status,
        "score": submission.score,
        "log": submission.log,
        "code": submission.code,
        "language": submission.language,
        "exam_id": submission.exam_id,
        "created_at": submission.created_at.isoformat()
        if submission.created_at
        else None,
        "case_results": [
            {
                "case_name": item.case_name,
                "status": item.status,
                "time_used_ms": item.time_used_ms,
                "memory_used_kb": item.memory_used_kb,
                "input_data": item.input_data,
                "expected_output": item.expected_output,
                "actual_output": item.actual_output,
                "error_output": item.error_output,
            }
            for item in (submission.case_results or [])
        ],
    }
