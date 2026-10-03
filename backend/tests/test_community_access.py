"""社区访问控制回归：隐藏评论与标签审批权限。"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.persistence.community import ProblemCommunityRepository
from app.persistence.database import Base
from app.persistence.unit_of_work import UnitOfWork
from app.services.community import (
    AttachTagParams,
    CreateCommentParams,
    CreateSolutionParams,
    CreateTagParams,
    SolutionService,
    TagService,
)


@pytest.fixture
def db_session():
    """独立数据库允许请求关闭会话后重新查询已提交数据。"""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    engine.dispose()


def test_hidden_solution_comments_are_unavailable(
    client, db_session, student_user, sample_problem
):
    repository = ProblemCommunityRepository(db_session)
    service = SolutionService(repository, uow=UnitOfWork(db_session))
    solution = service.create(
        CreateSolutionParams(sample_problem.id, student_user.id, "题解", "解法")
    )
    comment = service.add_comment(
        CreateCommentParams(solution.id, student_user.id, "评论包含解法")
    )
    path = f"/api/problems/solutions/{solution.id}/comments"
    published = client.get(path)
    assert published.status_code == 200
    assert published.json()["items"][0]["id"] == comment.id

    service.hide(solution.id, student_user.id, "student")

    assert client.get(path).status_code == 404
    # 隐藏只影响访问，保留评论供作者后续管理。
    assert repository.get_comment_by_id(comment.id).content == "评论包含解法"


def test_missing_solution_comments_return_not_found(client):
    assert client.get("/api/problems/solutions/999999/comments").status_code == 404


def test_student_cannot_revoke_teacher_tag_approval(
    client, db_session, student_token, sample_problem
):
    repository = ProblemCommunityRepository(db_session)
    service = TagService(repository, uow=UnitOfWork(db_session))
    tag = service.create(CreateTagParams("teacher", "arrays", "数组"))
    problem_id = sample_problem.id
    service.attach(AttachTagParams(problem_id, tag.id, True, "teacher"))

    response = client.post(
        f"/api/tags/problems/{problem_id}/attach",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"tag_id": tag.id, "approved": False},
    )

    assert response.status_code == 403
    assert repository.get_tag_map(problem_id, tag.id).approved is True
    assert repository.list_problem_ids_by_tag(tag.id) == [problem_id]


@pytest.mark.parametrize("approved", [False, True])
def test_teacher_can_change_tag_approval(db_session, sample_problem, approved):
    repository = ProblemCommunityRepository(db_session)
    service = TagService(repository, uow=UnitOfWork(db_session))
    tag = service.create(CreateTagParams("teacher", "arrays", "数组"))
    service.attach(AttachTagParams(sample_problem.id, tag.id, not approved, "teacher"))

    service.attach(AttachTagParams(sample_problem.id, tag.id, approved, "teacher"))

    assert repository.get_tag_map(sample_problem.id, tag.id).approved is approved


def test_student_can_repeat_unapproved_tag_suggestion(db_session, sample_problem):
    repository = ProblemCommunityRepository(db_session)
    service = TagService(repository, uow=UnitOfWork(db_session))
    tag = service.create(CreateTagParams("teacher", "arrays", "数组"))
    params = AttachTagParams(sample_problem.id, tag.id, False, "student")
    service.attach(params)
    original = repository.get_tag_map(sample_problem.id, tag.id)

    service.attach(params)

    repeated = repository.get_tag_map(sample_problem.id, tag.id)
    assert repeated.id == original.id
    assert repeated.approved is False


def test_solution_list_includes_body_and_viewer_interaction_state(
    client, db_session, student_token, teacher_token, student_user, sample_problem
):
    repository = ProblemCommunityRepository(db_session)
    service = SolutionService(repository, uow=UnitOfWork(db_session))
    solution = service.create(
        CreateSolutionParams(sample_problem.id, student_user.id, "完整题解", "## 解法\n正文")
    )
    service.toggle_like(solution.id, student_user.id)
    service.toggle_favorite(solution.id, student_user.id)
    path = f"/api/problems/{sample_problem.id}/solutions"

    response = client.get(path, headers={"Authorization": f"Bearer {student_token}"})
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["content"] == "## 解法\n正文"
    assert item["liked_by_me"] is True
    assert item["favorited_by_me"] is True

    response = client.get(path, headers={"Authorization": f"Bearer {teacher_token}"})
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["content"] == "## 解法\n正文"
    assert item["liked_by_me"] is False
    assert item["favorited_by_me"] is False
    assert repository.get_solution_by_id(solution.id).view_count == 0


def test_solution_list_excludes_hidden_body_and_interactions(
    client, db_session, student_token, student_user, sample_problem
):
    service = SolutionService(
        ProblemCommunityRepository(db_session), uow=UnitOfWork(db_session)
    )
    solution = service.create(
        CreateSolutionParams(sample_problem.id, student_user.id, "隐藏题解", "隐藏正文")
    )
    service.hide(solution.id, student_user.id, "student")

    response = client.get(
        f"/api/problems/{sample_problem.id}/solutions",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["items"] == []


def test_public_problem_tags_follow_teacher_approval(client, db_session, sample_problem):
    """待审建议保留在库中，只有教师批准后才成为公开题目标签。"""
    repository = ProblemCommunityRepository(db_session)
    service = TagService(repository, uow=UnitOfWork(db_session))
    tag = service.create(CreateTagParams("teacher", "arrays", "数组"))
    problem_id = sample_problem.id
    path = f"/api/tags/problems/{problem_id}"
    service.attach(AttachTagParams(problem_id, tag.id, False, "student"))

    response = client.get(path)
    assert response.status_code == 200
    assert response.json() == []
    assert repository.get_tag_map(problem_id, tag.id).approved is False

    service.attach(AttachTagParams(problem_id, tag.id, True, "teacher"))
    assert [item["id"] for item in client.get(path).json()] == [tag.id]

    service.attach(AttachTagParams(problem_id, tag.id, False, "teacher"))
    assert client.get(path).json() == []
