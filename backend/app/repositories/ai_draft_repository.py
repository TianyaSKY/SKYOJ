"""AI 草稿数据访问。"""

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.ai_draft import AiDraft


class AiDraftRepository:
    """ai_drafts 表读写。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        user_id: int,
        task_type: str,
        title: str,
        request_payload: dict[str, Any],
        problem_id: Optional[int] = None,
        status: str = "pending",
    ) -> AiDraft:
        """创建草稿记录。"""
        draft = AiDraft(
            user_id=user_id,
            task_type=task_type,
            status=status,
            title=title,
            problem_id=problem_id,
            request_payload=json.dumps(request_payload, ensure_ascii=False),
        )
        self._db.add(draft)
        self._db.commit()
        self._db.refresh(draft)
        return draft

    def get_by_id(self, draft_id: int) -> Optional[AiDraft]:
        """按主键查询。"""
        return self._db.get(AiDraft, draft_id)

    def list_by_user(
        self,
        user_id: int,
        *,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[AiDraft]:
        """按用户列出草稿，新的在前。"""
        query = self._db.query(AiDraft).filter(AiDraft.user_id == user_id)
        if status:
            query = query.filter(AiDraft.status == status)
        if task_type:
            query = query.filter(AiDraft.task_type == task_type)
        return (
            query.order_by(AiDraft.id.desc()).limit(max(1, min(limit, 200))).all()
        )

    def mark_running(self, draft_id: int) -> Optional[AiDraft]:
        """将任务标记为运行中。"""
        draft = self.get_by_id(draft_id)
        if draft is None:
            return None
        draft.status = "running"
        draft.updated_at = datetime.utcnow()
        self._db.commit()
        self._db.refresh(draft)
        return draft

    def mark_success(
        self,
        draft_id: int,
        *,
        result_payload: dict[str, Any],
        title: Optional[str] = None,
    ) -> Optional[AiDraft]:
        """将任务标记为成功并写入结果。"""
        draft = self.get_by_id(draft_id)
        if draft is None:
            return None
        draft.status = "success"
        draft.result_payload = json.dumps(result_payload, ensure_ascii=False)
        draft.error_message = None
        if title:
            draft.title = title
        draft.updated_at = datetime.utcnow()
        self._db.commit()
        self._db.refresh(draft)
        return draft

    def mark_failed(self, draft_id: int, error_message: str) -> Optional[AiDraft]:
        """将任务标记为失败。"""
        draft = self.get_by_id(draft_id)
        if draft is None:
            return None
        draft.status = "failed"
        draft.error_message = error_message[:2000]
        draft.updated_at = datetime.utcnow()
        self._db.commit()
        self._db.refresh(draft)
        return draft

    def mark_consumed(self, draft_id: int) -> Optional[AiDraft]:
        """标记草稿已被应用到正式题目。"""
        draft = self.get_by_id(draft_id)
        if draft is None:
            return None
        draft.consumed_at = datetime.utcnow()
        draft.updated_at = datetime.utcnow()
        self._db.commit()
        self._db.refresh(draft)
        return draft

    def delete(self, draft: AiDraft) -> None:
        """删除草稿。"""
        self._db.delete(draft)
        self._db.commit()

    def count_stats(self, user_id: int) -> dict[str, int]:
        """统计用户草稿各状态数量。"""
        rows = (
            self._db.query(AiDraft.status, func.count(AiDraft.id))
            .filter(AiDraft.user_id == user_id)
            .group_by(AiDraft.status)
            .all()
        )
        by_status = {status: count for status, count in rows}
        total = sum(by_status.values())
        unconsumed_success = (
            self._db.query(func.count(AiDraft.id))
            .filter(
                AiDraft.user_id == user_id,
                AiDraft.status == "success",
                AiDraft.consumed_at.is_(None),
            )
            .scalar()
            or 0
        )
        return {
            "total": total,
            "pending": by_status.get("pending", 0),
            "running": by_status.get("running", 0),
            "success": by_status.get("success", 0),
            "failed": by_status.get("failed", 0),
            "unconsumed_success": int(unconsumed_success),
        }

    @staticmethod
    def parse_json_field(raw: Optional[str]) -> dict[str, Any]:
        """将 Text 字段解析为 dict。"""
        if not raw:
            return {}
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {"value": data}
        except json.JSONDecodeError:
            return {"raw": raw}
