"""搜索服务按角色过滤测试。"""

from types import SimpleNamespace

from app.services.search_facade_service import SearchFacadeService


class FakeSearchRepository:
    """用于验证搜索服务的内存仓储。"""

    def __init__(self, problems) -> None:
        self._problems = problems

    def search_problems(self, query: str, top_k: int):
        return list(self._problems)

    def add_history(self, user_id: int, query: str) -> None:
        pass


class FakeTestCaseStorage:
    """内存假测试用例存储：仅 1、3 号题目已有测试用例。"""

    def has_test_cases(self, problem_id: int) -> bool:
        return problem_id in {1, 3}


def _problems():
    return [
        SimpleNamespace(
            id=problem_id,
            title=f"题目{problem_id}",
            content="内容",
            type="acm",
            language="python",
            time_limit=1000,
            memory_limit=128,
            template_code="",
            test_case_path=None,
            created_at=None,
        )
        for problem_id in (1, 2, 3)
    ]


def test_search_student_filters_out_problems_without_test_cases() -> None:
    service = SearchFacadeService(
        FakeSearchRepository(_problems()), test_case_storage=FakeTestCaseStorage()
    )

    results = service.search(1, "题目", 10, "student")

    assert [item.id for item in results] == [1, 3]


def test_search_teacher_sees_all_problems() -> None:
    service = SearchFacadeService(
        FakeSearchRepository(_problems()), test_case_storage=FakeTestCaseStorage()
    )

    results = service.search(1, "题目", 10, "teacher")

    assert [item.id for item in results] == [1, 2, 3]
