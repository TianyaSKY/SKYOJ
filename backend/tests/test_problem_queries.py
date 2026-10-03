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
                    type="oop" if problem_id in (1, 3) else "acm",
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


@pytest.mark.parametrize('role', ['teacher', 'student'])
def test_type_tag_and_visibility_filter_before_count_and_pagination(service, role):
    first = service.list_problems(role, page=1, page_size=1, tag_id=1, problem_type='oop')
    second = service.list_problems(role, page=2, page_size=1, tag_id=1, problem_type='oop')
    assert first.total == second.total == 2
    assert [item.id for item in first.problems] == [3]
    assert [item.id for item in second.problems] == [1]


def test_problem_list_api_filters_type_before_pagination(client, db_session, teacher_token):
    selected = Problem(title='OOP题目', content='正文', type='oop', language='python')
    db_session.add(selected)
    db_session.flush()
    selected_id = selected.id
    db_session.add_all([Problem(title='ACM题目', content='正文', type='acm', language='python') for _ in range(2)])
    db_session.commit()
    response = client.get('/api/problems/', headers={'Authorization': f'Bearer {teacher_token}'}, params={
        'page': 1, 'page_size': 1, 'problem_type': 'oop',
    })
    assert response.status_code == 200
    assert response.json()['total'] == 1
    assert response.json()['problems'][0]['id'] == selected_id


def test_problem_list_api_rejects_invalid_type(client, teacher_token):
    response = client.get('/api/problems/', headers={'Authorization': f'Bearer {teacher_token}'}, params={'problem_type': 'invalid'})
    assert response.status_code == 422
