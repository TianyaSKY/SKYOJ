"""plagiarism 业务参数、结果与服务。"""

from __future__ import annotations

from app.core.errors import PermissionDeniedError, ResourceNotFoundError
from app.core.json import JsonValue
from dataclasses import asdict, dataclass
from datetime import datetime
from loguru import logger
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app.services.submission import SubmissionRecord


@dataclass(frozen=True)
class PlagiarismScanParams:
    problem_id: int
    min_similarity: float = 0.3


@dataclass(frozen=True)
class MatchedBlock:
    start_a: int
    end_a: int
    start_b: int
    end_b: int
    code_a: str
    code_b: str


@dataclass(frozen=True)
class SimilarityPair:
    submission_a_id: int
    submission_b_id: int
    score: float
    matched_blocks: list[MatchedBlock]


@dataclass(frozen=True)
class PlagiarismResult:
    problem_id: int
    total_pairs: int
    high_risk_pairs: list[SimilarityPair]


@dataclass(frozen=True)
class PlagiarismReportItem:
    id: int
    submission_a_id: int
    submission_b_id: int
    username_a: str
    username_b: str
    similarity_score: float
    matched_blocks: list[MatchedBlock]
    status: str
    created_at: datetime | None


@dataclass(frozen=True)
class PaginatedPlagiarismReports:
    total: int
    page: int
    page_size: int
    reports: list[PlagiarismReportItem]


@dataclass
class PlagiarismReportRecord:
    """PlagiarismReport 的数据库快照；不携带 ORM 或 Session。"""

    id: int
    problem_id: int
    submission_a_id: int
    submission_b_id: int
    similarity_score: float | None
    matched_blocks: list[dict[str, JsonValue]] | None
    status: str | None
    jplag_result_id: str | None
    created_at: datetime | None
    updated_at: datetime | None
    submission_a: SubmissionRecord | None
    submission_b: SubmissionRecord | None


from app.clients.jplag_client import JPlagAPIError, JPlagClient
from app.messaging.queues import JUDGE_QUEUE
from app.messaging.task_names import SCAN_PLAGIARISM_TASK
from app.persistence.submission import PlagiarismRepository, SubmissionRepository
from app.services.async_job import AsyncJobService, CreateAsyncJobParams


class PlagiarismService:
    def __init__(
        self,
        plagiarism_repo: PlagiarismRepository,
        submission_repo: SubmissionRepository,
        jplag_client: JPlagClient | None = None,
        job_service: AsyncJobService | None = None,
    ) -> None:
        self._plagiarism_repo = plagiarism_repo
        self._submission_repo = submission_repo
        self._jplag_client = jplag_client or JPlagClient()
        self._job_service = job_service

    def trigger_scan(self, problem_id: int) -> int:
        """创建 AsyncJob 并返回 job_id。"""
        if self._job_service is None:
            raise RuntimeError("查重任务服务未注入")
        job = self._job_service.enqueue(
            CreateAsyncJobParams(
                task_name=SCAN_PLAGIARISM_TASK,
                queue=JUDGE_QUEUE,
                payload={"problem_id": problem_id, "min_similarity": 0.3},
                dedupe_key=f"plagiarism-scan:{problem_id}",
                max_attempts=1,
            )
        )
        return job.id

    def trigger_manual_scan(self, problem_id: int, requester_role: str) -> int:
        """教师手动触发查重，返回 job_id。"""
        self._require_teacher(requester_role)
        return self.trigger_scan(problem_id)

    def run_scan(
        self,
        problem_id: int,
        min_similarity: float = 0.3,
    ) -> PlagiarismResult:
        """在 Celery worker 中执行：取提交 → 调用 JPlag → 写入报告。"""

        submissions = self._submission_repo.list_accepted_for_plagiarism(problem_id)

        if len(submissions) < 2:
            logger.info("题目 #{} 有效提交不足，跳过查重", problem_id)
            return PlagiarismResult(
                problem_id=problem_id,
                total_pairs=0,
                high_risk_pairs=[],
            )

        sub_list = [
            {
                "id": s.id,
                "code": s.code_content or "",
                "language": s.language or "python",
                "filename": self._filename_for_language(s.language),
                "user_id": s.user_id,
            }
            for s in submissions
        ]
        language = submissions[0].language or "python"

        try:
            similarity_pairs = self._jplag_client.compare(sub_list, language=language)
        except JPlagAPIError as exc:
            logger.error("JPlag API 调用失败 problem_id={} error={}", problem_id, exc)
            raise

        high_risk: list[SimilarityPair] = []
        with self._plagiarism_repo.unit_of_work.transaction():
            for pair in similarity_pairs:
                if pair.score < min_similarity:
                    continue
                self._plagiarism_repo.upsert_report(
                    problem_id=problem_id,
                    sub_a=pair.submission_a_id,
                    sub_b=pair.submission_b_id,
                    score=pair.score,
                    blocks=[asdict(b) for b in pair.matched_blocks],
                    status="completed",
                )
                high_risk.append(pair)

        logger.info(
            "题目 #{} 查重完成，共 {} 对提交，发现 {} 对高相似度",
            problem_id,
            len(submissions),
            len(high_risk),
        )
        return PlagiarismResult(
            problem_id=problem_id,
            total_pairs=len(submissions),
            high_risk_pairs=high_risk,
        )

    def get_problem_reports(
        self,
        problem_id: int,
        min_score: float,
        page: int,
        page_size: int,
        requester_id: int,
        requester_role: str,
    ) -> PaginatedPlagiarismReports:
        self._require_teacher(requester_role)
        reports, total = self._plagiarism_repo.get_reports_for_problem(
            problem_id, min_score, page, page_size
        )
        return PaginatedPlagiarismReports(
            total,
            page,
            page_size,
            [self._report_to_item(r) for r in reports],
        )

    def get_submission_reports(
        self, submission_id: int, requester_id: int, requester_role: str
    ) -> list[PlagiarismReportItem]:
        submission = self._submission_repo.get_by_id(submission_id)
        if submission is None:
            raise ResourceNotFoundError("提交记录不存在")
        if requester_role == "student" and submission.user_id != requester_id:
            raise PermissionDeniedError("无权查看该提交记录")

        reports = self._plagiarism_repo.get_by_submission_id(submission_id)
        return [self._report_to_item(r) for r in reports]

    def _report_to_item(self, report) -> PlagiarismReportItem:
        sub_a = report.submission_a
        sub_b = report.submission_b
        return PlagiarismReportItem(
            id=report.id,
            submission_a_id=report.submission_a_id,
            submission_b_id=report.submission_b_id,
            username_a=sub_a.user.username if sub_a and sub_a.user else "",
            username_b=sub_b.user.username if sub_b and sub_b.user else "",
            similarity_score=report.similarity_score,
            matched_blocks=[
                MatchedBlock(**block) for block in (report.matched_blocks or [])
            ],
            status=report.status,
            created_at=report.created_at,
        )

    @staticmethod
    def _require_teacher(role: str) -> None:
        if role != "teacher":
            raise PermissionDeniedError("仅教师可操作题目查重")

    @staticmethod
    def _filename_for_language(language: str | None) -> str:
        lang = (language or "python").lower()
        ext_map = {
            "python": "py",
            "py": "py",
            "java": "java",
            "c": "c",
            "cpp": "cpp",
            "c++": "cpp",
            "go": "go",
            "rust": "rs",
            "javascript": "js",
            "js": "js",
            "typescript": "ts",
            "ts": "ts",
        }
        return f"main.{ext_map.get(lang, 'py')}"
