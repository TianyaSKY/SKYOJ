"""题目测试点管理 API 测试。"""

from app.api.auth_context import AuthContext, get_current_auth
from app.api.deps import get_problem_service
from app.services.auth import AuthUserInfo
from app.services.problem import TestCaseItem as ProblemTestCaseItem
from app.services.problem import TestCaseSummary as ProblemTestCaseSummary


class FakeProblemService:
    """返回固定测试点摘要的题目服务。"""

    def get_test_case_summary(self, requester_role: str, problem_id: int):
        assert requester_role == "teacher"
        assert problem_id == 7
        return ProblemTestCaseSummary(
            status="incomplete",
            total_count=2,
            valid_count=1,
            invalid_count=1,
            file_count=3,
            total_size=12,
            ignored_files=["README.txt"],
            cases=[
                ProblemTestCaseItem(
                    name="1",
                    input_file="1.in",
                    output_file="1.out",
                    input_size=5,
                    output_size=5,
                    status="ready",
                ),
                ProblemTestCaseItem(
                    name="2",
                    input_file="2.in",
                    output_file=None,
                    input_size=2,
                    output_size=None,
                    status="missing_output",
                ),
            ],
        )


def test_teacher_test_case_summary_endpoint_serializes_status(client):
    client.app.dependency_overrides[get_current_auth] = lambda: AuthContext(
        user=AuthUserInfo(id=1, username="teacher", role="teacher")
    )
    client.app.dependency_overrides[get_problem_service] = FakeProblemService

    response = client.get("/api/problems/7/test_cases/summary")

    assert response.status_code == 200
    assert response.json() == {
        "status": "incomplete",
        "total_count": 2,
        "valid_count": 1,
        "invalid_count": 1,
        "file_count": 3,
        "total_size": 12,
        "ignored_files": ["README.txt"],
        "cases": [
            {
                "name": "1",
                "input_file": "1.in",
                "output_file": "1.out",
                "input_size": 5,
                "output_size": 5,
                "status": "ready",
            },
            {
                "name": "2",
                "input_file": "2.in",
                "output_file": None,
                "input_size": 2,
                "output_size": None,
                "status": "missing_output",
            },
        ],
    }
