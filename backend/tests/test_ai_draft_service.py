"""AI 草稿箱 Service 单元测试（内存假仓储）。"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import pytest

from app.domain.ai_draft import (
    STATUS_PENDING,
    STATUS_SUCCESS,
    TASK_PROBLEM_GENERATION,
    SubmitProblemGenerationParams,
    SubmitTestScriptGenerationParams,
)
from app.domain.errors import InvalidStateError, LlmConfigError, ResourceNotFoundError
from app.services.ai_draft_service import AiDraftService


@dataclass
class FakeDraft:
    id: int
    user_id: int
    task_type: str
    status: str
    title: str
    problem_id: Optional[int]
    request_payload: str
    result_payload: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = field(default_factory=datetime.utcnow)
    consumed_at: Optional[datetime] = None


class FakeDraftRepository:
    def __init__(self) -> None:
        self._items: dict[int, FakeDraft] = {}
        self._seq = 1

    def create(
        self,
        *,
        user_id: int,
        task_type: str,
        title: str,
        request_payload: dict[str, Any],
        problem_id: Optional[int] = None,
        status: str = "pending",
    ) -> FakeDraft:
        import json

        draft = FakeDraft(
            id=self._seq,
            user_id=user_id,
            task_type=task_type,
            status=status,
            title=title,
            problem_id=problem_id,
            request_payload=json.dumps(request_payload, ensure_ascii=False),
        )
        self._items[self._seq] = draft
        self._seq += 1
        return draft

    def get_by_id(self, draft_id: int) -> Optional[FakeDraft]:
        return self._items.get(draft_id)

    def list_by_user(self, user_id: int, **kwargs) -> list[FakeDraft]:
        return [d for d in self._items.values() if d.user_id == user_id]

    def mark_consumed(self, draft_id: int) -> Optional[FakeDraft]:
        draft = self.get_by_id(draft_id)
        if draft:
            draft.consumed_at = datetime.utcnow()
        return draft

    def delete(self, draft: FakeDraft) -> None:
        self._items.pop(draft.id, None)

    def count_stats(self, user_id: int) -> dict[str, int]:
        items = [d for d in self._items.values() if d.user_id == user_id]
        return {
            "total": len(items),
            "pending": sum(1 for d in items if d.status == "pending"),
            "running": sum(1 for d in items if d.status == "running"),
            "success": sum(1 for d in items if d.status == "success"),
            "failed": sum(1 for d in items if d.status == "failed"),
            "unconsumed_success": sum(
                1 for d in items if d.status == "success" and d.consumed_at is None
            ),
        }

    @staticmethod
    def parse_json_field(raw: Optional[str]) -> dict[str, Any]:
        import json

        if not raw:
            return {}
        return json.loads(raw)


@dataclass
class FakeProblem:
    id: int
    title: str
    content: str
    type: str = "acm"
    language: str = "python"
    time_limit: int = 1000
    memory_limit: int = 128
    template_code: str = ""


class FakeProblemRepository:
    def __init__(self) -> None:
        self._items: dict[int, FakeProblem] = {
            1: FakeProblem(id=1, title="A+B", content="add"),
        }
        self._seq = 2

    def get_by_id(self, problem_id: int) -> Optional[FakeProblem]:
        return self._items.get(problem_id)

    def create(self, **kwargs) -> FakeProblem:
        problem = FakeProblem(
            id=self._seq,
            title=kwargs["title"],
            content=kwargs["content"],
            type=kwargs.get("problem_type", "acm"),
            language=kwargs.get("language", "python"),
            time_limit=kwargs.get("time_limit", 1000),
            memory_limit=kwargs.get("memory_limit", 128),
            template_code=kwargs.get("template_code", ""),
        )
        self._items[self._seq] = problem
        self._seq += 1
        return problem


class FakeQueue:
    def __init__(self) -> None:
        self.jobs: list[tuple] = []

    def enqueue(self, func, *args, **kwargs) -> None:
        self.jobs.append((func, args, kwargs))


class ReadyLlm:
    def is_configured(self) -> bool:
        return True


class NotReadyLlm:
    def is_configured(self) -> bool:
        return False


def _service(
    drafts=None,
    problems=None,
    queue=None,
    llm=None,
) -> AiDraftService:
    return AiDraftService(
        draft_repository=drafts or FakeDraftRepository(),
        problem_repository=problems or FakeProblemRepository(),
        task_queue=queue or FakeQueue(),
        llm_client=llm or ReadyLlm(),
    )


def test_submit_problem_generation_enqueues_job():
    drafts = FakeDraftRepository()
    queue = FakeQueue()
    service = _service(drafts=drafts, queue=queue)

    result = service.submit_problem_generation(
        SubmitProblemGenerationParams(
            user_id=9,
            background="字符串统计",
            difficulty="简单",
        )
    )

    assert result.draft_id == 1
    assert result.status == STATUS_PENDING
    assert result.task_type == TASK_PROBLEM_GENERATION
    assert len(queue.jobs) == 1
    assert drafts.get_by_id(1).user_id == 9


def test_submit_problem_generation_requires_llm_config():
    service = _service(llm=NotReadyLlm())
    with pytest.raises(LlmConfigError):
        service.submit_problem_generation(
            SubmitProblemGenerationParams(
                user_id=1,
                background="x",
                difficulty="简单",
            )
        )


def test_submit_test_script_missing_problem():
    service = _service()
    with pytest.raises(ResourceNotFoundError):
        service.submit_test_script_generation(
            SubmitTestScriptGenerationParams(
                user_id=1,
                problem_id=999,
                direction="",
                count=10,
                range_info="",
            )
        )


def test_apply_problem_draft_success():
    import json

    drafts = FakeDraftRepository()
    problems = FakeProblemRepository()
    service = _service(drafts=drafts, problems=problems)

    draft = drafts.create(
        user_id=1,
        task_type=TASK_PROBLEM_GENERATION,
        title="tmp",
        request_payload={"background": "x"},
        status=STATUS_SUCCESS,
    )
    draft.result_payload = json.dumps(
        {
            "title": "统计元音",
            "content": "给定字符串...",
            "type": "acm",
            "language": "python",
            "time_limit": 1000,
            "memory_limit": 128,
            "template_code": "",
        },
        ensure_ascii=False,
    )
    draft.status = STATUS_SUCCESS

    result = service.apply_problem_draft(1, draft.id)
    assert result.problem_id >= 2
    assert result.title == "统计元音"
    assert drafts.get_by_id(draft.id).consumed_at is not None


def test_apply_non_success_draft_fails():
    drafts = FakeDraftRepository()
    service = _service(drafts=drafts)
    draft = drafts.create(
        user_id=1,
        task_type=TASK_PROBLEM_GENERATION,
        title="tmp",
        request_payload={},
        status=STATUS_PENDING,
    )
    with pytest.raises(InvalidStateError):
        service.apply_problem_draft(1, draft.id)
