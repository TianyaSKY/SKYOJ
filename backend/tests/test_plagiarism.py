"""查重功能单元测试。"""

from unittest.mock import MagicMock, patch

import pytest

from app.domain.plagiarism import MatchedBlock, SimilarityPair
from app.clients.jplag_client import JPlagClient


class TestJPlagClient:
    """JPlagClient 的单元测试（mock HTTP 层）。"""

    def test_compare_returns_empty_for_single_submission(self):
        """只有一份提交时应返回空列表。"""
        client = JPlagClient()
        result = client.compare([{"id": 1, "code": "print(1)"}])
        assert result == []

    def test_compare_resolves_language_from_extension(self):
        """能根据文件扩展名自动识别语言。"""
        client = JPlagClient()
        lang = client._resolve_language(None, [{"id": 1, "filename": "Main.java"}])
        assert lang == "java"

    def test_resolve_language_from_explicit(self):
        """显式传入语言参数优先。"""
        client = JPlagClient()
        lang = client._resolve_language("cpp", [{"id": 1, "filename": "main.c"}])
        assert lang == "cpp"

    @patch("app.clients.jplag_client.requests.post")
    def test_compare_posts_to_correct_endpoint(self, mock_post):
        """验证请求发往 JPlag 的 /api/run 端点。"""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "abc123", "status": "completed", "matches": []},
        )

        client = JPlagClient()
        with patch.object(client, "_poll_result", return_value=[]):
            client.compare(
                [{"id": 1, "code": "x = 1"}, {"id": 2, "code": "x = 2"}],
                language="python",
            )

        mock_post.assert_called_once()
        call_url = mock_post.call_args[0][0]
        assert call_url.endswith("/api/run")

    @patch("app.clients.jplag_client.requests.post")
    def test_compare_polls_until_completed(self, mock_post):
        """验证 JPlag 返回非 completed 状态时轮询。"""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(
                side_effect=[
                    {"id": "abc123", "status": "pending"},
                    {"id": "abc123", "status": "completed", "matches": []},
                ]
            ),
        )

        client = JPlagClient()
        with patch("app.clients.jplag_client.time.sleep"):
            with patch("app.clients.jplag_client.JPlagClient._poll_result") as mock_poll:
                mock_poll.return_value = []
                client.compare(
                    [{"id": 1, "code": "x = 1"}, {"id": 2, "code": "x = 2"}],
                    language="python",
                )

    def test_extract_lines_within_bounds(self):
        """行号超出范围时不应崩溃。"""
        code = "line1\nline2\nline3"
        result = JPlagClient._extract_lines(code, start=1, end=10)
        assert result == code

    def test_extract_lines_empty_code(self):
        """空代码不应崩溃。"""
        result = JPlagClient._extract_lines("", start=1, end=5)
        assert result == ""


class TestPlagiarismService:
    """PlagiarismService 的单元测试（mock 所有依赖）。"""

    def test_trigger_scan_creates_job(self):
        """trigger_scan 应调用 enqueue 创建 AsyncJob。"""
        from app.services.plagiarism_service import PlagiarismService

        mock_plagiarism_repo = MagicMock()
        mock_submission_repo = MagicMock()
        mock_job_service = MagicMock()
        mock_job_service.enqueue.return_value = MagicMock(id=42)

        with patch(
            "app.services.plagiarism_service.AsyncJobService.from_session",
            return_value=mock_job_service,
        ):
            service = PlagiarismService(
                plagiarism_repo=mock_plagiarism_repo,
                submission_repo=mock_submission_repo,
            )
            job_id = service.trigger_scan(MagicMock(), problem_id=5)

        assert job_id == 42
        mock_job_service.enqueue.assert_called_once()

    def test_run_scan_writes_reports_for_high_similarity_pairs(self):
        """run_scan 应将高相似度对的报告写入数据库。"""
        from app.services.plagiarism_service import PlagiarismService

        mock_plagiarism_repo = MagicMock()
        mock_submission_repo = MagicMock()
        mock_db = MagicMock()
        mock_jplag = MagicMock()
        mock_jplag.compare.return_value = [
            SimilarityPair(
                submission_a_id=1,
                submission_b_id=2,
                score=0.85,
                matched_blocks=[
                    MatchedBlock(
                        start_a=1, end_a=5,
                        start_b=3, end_b=7,
                        code_a="for i in range(n):",
                        code_b="for j in range(n):",
                    )
                ],
            )
        ]

        mock_sub_a = MagicMock(
            id=1,
            problem_id=1,
            status="Accepted",
            code_content="x = 1",
            language="python",
        )
        mock_sub_a.user = MagicMock(username="alice")
        mock_sub_b = MagicMock(
            id=2,
            problem_id=1,
            status="Accepted",
            code_content="x = 2",
            language="python",
        )
        mock_sub_b.user = MagicMock(username="bob")
        mock_db.query.return_value.filter.return_value.options.return_value.all.return_value = [
            mock_sub_a,
            mock_sub_b,
        ]

        service = PlagiarismService(
            plagiarism_repo=mock_plagiarism_repo,
            submission_repo=mock_submission_repo,
            jplag_client=mock_jplag,
        )

        with patch.object(
            service,
            "_filename_for_language",
            return_value="main.py",
        ):
            result = service.run_scan(
                db=mock_db,
                problem_id=1,
                min_similarity=0.3,
            )

        assert result.problem_id == 1
        assert len(result.high_risk_pairs) == 1
        assert result.high_risk_pairs[0].score == 0.85
        mock_plagiarism_repo.upsert_report.assert_called_once()

    def test_run_scan_skips_low_similarity_pairs(self):
        """run_scan 应跳过低于阈值的相似对。"""
        from app.services.plagiarism_service import PlagiarismService

        mock_plagiarism_repo = MagicMock()
        mock_submission_repo = MagicMock()
        mock_db = MagicMock()
        mock_jplag = MagicMock()
        mock_jplag.compare.return_value = [
            SimilarityPair(
                submission_a_id=1,
                submission_b_id=2,
                score=0.1,  # 低于默认阈值 0.3
                matched_blocks=[],
            )
        ]

        service = PlagiarismService(
            plagiarism_repo=mock_plagiarism_repo,
            submission_repo=mock_submission_repo,
            jplag_client=mock_jplag,
        )

        with patch.object(
            service,
            "_filename_for_language",
            return_value="main.py",
        ):
            result = service.run_scan(
                db=mock_db,
                problem_id=1,
                min_similarity=0.3,
            )

        assert len(result.high_risk_pairs) == 0
        mock_plagiarism_repo.upsert_report.assert_not_called()


class TestPlagiarismRepository:
    """PlagiarismRepository 的单元测试。"""

    def test_upsert_inserts_new_report(self):
        """upsert 应在记录不存在时插入。"""
        from app.repositories.plagiarism_repository import PlagiarismRepository

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.count.return_value = 0

        repo = PlagiarismRepository(mock_db)
        with patch("app.repositories.plagiarism_repository.PlagiarismReport"):
            result = repo.upsert_report(
                problem_id=1,
                sub_a=5,
                sub_b=10,
                score=0.7,
                blocks=[],
                status="completed",
            )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()

    def test_report_to_dict_includes_all_fields(self):
        """_report_to_dict 应包含所有必要字段。"""
        from app.services.plagiarism_service import PlagiarismService

        mock_report = MagicMock()
        mock_report.id = 1
        mock_report.submission_a_id = 5
        mock_report.submission_b_id = 10
        mock_report.submission_a.user.username = "alice"
        mock_report.submission_b.user.username = "bob"
        mock_report.similarity_score = 0.75
        mock_report.matched_blocks = [{"start_a": 1, "end_a": 5}]
        mock_report.status = "completed"
        mock_report.created_at = None

        service = PlagiarismService(
            plagiarism_repo=MagicMock(),
            submission_repo=MagicMock(),
        )
        result = service._report_to_dict(mock_report)

        assert result["id"] == 1
        assert result["username_a"] == "alice"
        assert result["username_b"] == "bob"
        assert result["similarity_score"] == 0.75
        assert result["status"] == "completed"
