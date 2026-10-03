"""搜索服务按角色过滤测试。"""

import pytest

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.search import SearchFacadeService


class FakeSearchRepository:
    """用于验证搜索服务的内存仓储。"""

    def __init__(self, problems) -> None:
        self.unit_of_work = MagicMock()
        self._problems = problems

    def search_problems(self, query: str, top_k: int, *, visible_ids=None):
        return [problem for problem in self._problems if visible_ids is None or problem.id in visible_ids][:top_k]

    def add_history(self, user_id: int, query: str) -> None:
        pass


class FakeTestCaseStorage:
    """内存假测试用例存储：仅 1、3 号题目已有测试用例。"""

    def list_problem_ids_with_test_cases(self):
        return frozenset({1, 3})

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
        FakeSearchRepository(_problems()),
        test_case_storage=FakeTestCaseStorage(),
        uow=MagicMock(),
    )

    results = service.search(1, "题目", 10, "student")

    assert [item.id for item in results] == [1, 3]


def test_search_teacher_sees_all_problems() -> None:
    service = SearchFacadeService(
        FakeSearchRepository(_problems()),
        test_case_storage=FakeTestCaseStorage(),
        uow=MagicMock(),
    )

    results = service.search(1, "题目", 10, "teacher")

    assert [item.id for item in results] == [1, 2, 3]

def test_student_search_limit_applies_after_visibility_filter(db_session, student_user, tmp_path):
    from app.clients.problem_test_case_storage_client import ProblemTestCaseStorageClient
    from app.persistence.problem import Problem
    from app.persistence.unit_of_work import UnitOfWork
    from app.persistence.user import SearchRepository

    problems = [Problem(title=f"关键词题目{index}", content="正文", type="acm", language="python") for index in range(3)]
    db_session.add_all(problems)
    db_session.commit()
    visible_id = problems[-1].id
    folder = tmp_path / str(visible_id)
    folder.mkdir()
    (folder / '1.in').write_text('1')
    service = SearchFacadeService(
        SearchRepository(db_session),
        test_case_storage=ProblemTestCaseStorageClient(str(tmp_path)),
        uow=UnitOfWork(db_session),
    )

    results = service.search(student_user.id, "关键词", 1, "student")

    assert [item.id for item in results] == [visible_id]


@pytest.mark.parametrize('query, distractor', [('%', '百分比'), ('_', 'a'), ('__init__', 'xxinitxx'), ('a/b', 'aXb'), ('a/%_', 'a/abc')])
@pytest.mark.parametrize('field', ['title', 'content'])
def test_keyword_search_matches_special_characters_literally(db_session, query, distractor, field):
    from app.persistence.problem import Problem
    from app.persistence.user import SearchRepository

    matching = Problem(title='匹配题目', content='正文', type='acm', language='python')
    other = Problem(title='其他题目', content='正文', type='acm', language='python')
    setattr(matching, field, f'前缀{query}后缀')
    setattr(other, field, f'前缀{distractor}后缀')
    db_session.add_all([matching, other])
    db_session.commit()

    results = SearchRepository(db_session).search_problems(query, 10)

    assert [item.id for item in results] == [matching.id]
