"""真实仓储验证标签、可见性均在数据库计数和分页之前生效。"""

import pytest
from app.clients.problem_test_case_storage_client import ProblemTestCaseStorageClient
from app.persistence.community import ProblemTag, ProblemTagMap
from app.persistence.database import Base
from app.persistence.problem import Problem, ProblemRepository
from app.persistence.unit_of_work import UnitOfWork
from app.services.problem import ProblemService
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.fixture
def service(tmp_path):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(ProblemTag(id=1, slug="tag", name="标签"))
        for problem_id in range(1, 7):
            db.add(
                Problem(
                    id=problem_id,
                    title=f"题目{problem_id}",
                    content="内容",
                    type="acm",
                    language="python",
                )
            )
        db.flush()
        for problem_id in (1, 3, 5, 6):
            db.add(
                ProblemTagMap(problem_id=problem_id, tag_id=1, approved=problem_id != 6)
            )
        db.commit()
        storage = ProblemTestCaseStorageClient(str(tmp_path))
        for problem_id in (1, 3, 4, 6):
            folder = tmp_path / str(problem_id)
            folder.mkdir()
            (folder / "1.in").write_text("1")
        # 空目录和暂存目录不构成可见题目。
        (tmp_path / "5").mkdir()
        (tmp_path / ".trash").mkdir()
        yield ProblemService(ProblemRepository(db), storage, uow=UnitOfWork(db))
    engine.dispose()


def test_teacher_tag_filter_paginates_matching_rows(service):
    first = service.list_problems("teacher", page=1, page_size=2, tag_id=1)
    second = service.list_problems("teacher", page=2, page_size=2, tag_id=1)
    assert first.total == second.total == 3
    assert [item.id for item in first.problems] == [5, 3]
    assert [item.id for item in second.problems] == [1]


def test_student_visibility_and_tag_are_intersected_before_pagination(service):
    result = service.list_problems("student", page=2, page_size=1, tag_id=1)
    assert result.total == 2
    assert [item.id for item in result.problems] == [1]


def test_unknown_tag_and_out_of_range_page_keep_correct_total(service):
    result = service.list_problems("teacher", page=1, page_size=2, tag_id=999)
    assert result.total == 0 and result.problems == []
    result = service.list_problems("teacher", page=8, page_size=2, tag_id=1)
    assert result.total == 3 and result.problems == []
