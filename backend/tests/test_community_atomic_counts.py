"""社区交互计数不依赖旧题解快照，编辑与重复删除不能覆盖有效计数。"""

import pytest
from copy import deepcopy

from app.core.errors import ResourceNotFoundError
from app.persistence.community import ProblemCommunityRepository, ProblemSolutionComment, ProblemSolutionLike, ProblemSolutionFavorite
from app.persistence.unit_of_work import UnitOfWork
from app.services.community import SolutionService, CreateSolutionParams, CreateCommentParams, UpdateSolutionParams


@pytest.fixture
def community(db_session, sample_problem, student_user):
    repo = ProblemCommunityRepository(db_session)
    service = SolutionService(repo, uow=UnitOfWork(db_session))
    created = service.create(CreateSolutionParams(sample_problem.id, student_user.id, '题解', '正文'))
    return repo, service, created.id


def test_interactions_using_old_snapshots_preserve_all_counts(community, student_user, teacher_user, db_session, monkeypatch):
    repo, service, solution_id = community
    stale = repo.get_solution_by_id(solution_id)
    for user_id in [student_user.id, teacher_user.id]:
        # 模拟请求在其他事务提交之前已经读到旧快照。
        with monkeypatch.context() as patch:
            patch.setattr(repo, 'get_solution_by_id', lambda ignored: deepcopy(stale))
            service.toggle_like(solution_id, user_id)
            service.toggle_favorite(solution_id, user_id)
            service.add_comment(CreateCommentParams(solution_id, user_id, 'comment'))
            service.get(solution_id, user_id)
    current = repo.get_solution_by_id(solution_id)
    assert (current.vote_count, current.favorite_count, current.comment_count, current.view_count) == (2, 2, 2, 2)
    assert db_session.query(ProblemSolutionLike).count() == 2
    assert db_session.query(ProblemSolutionFavorite).count() == 2
    assert db_session.query(ProblemSolutionComment).count() == 2
    # 编辑来自更早的快照，不得把这些计数重新写成旧值。
    stale.vote_count = stale.favorite_count = stale.comment_count = stale.view_count = 0
    stale.title = '更新标题'
    repo.update_solution(solution_id, title=stale.title)
    db_session.commit()
    current = repo.get_solution_by_id(solution_id)
    assert current.title == '更新标题'
    assert (current.vote_count, current.favorite_count, current.comment_count, current.view_count) == (2, 2, 2, 2)


def test_repeated_comment_delete_does_not_decrement_other_comments(community, student_user, monkeypatch):
    repo, service, solution_id = community
    first = service.add_comment(CreateCommentParams(solution_id, student_user.id, 'first'))
    second = service.add_comment(CreateCommentParams(solution_id, student_user.id, 'second'))
    stale = repo.get_comment_by_id(first.id)
    service.delete_comment(first.id, student_user.id, 'student')
    monkeypatch.setattr(repo, 'get_comment_by_id', lambda ignored: stale)
    with pytest.raises(ResourceNotFoundError):
        service.delete_comment(first.id, student_user.id, 'student')
    assert repo.get_solution_by_id(solution_id).comment_count == 1
    rows, total = repo.list_comments(solution_id, 1, 50)
    assert total == 1 and rows[0].id == second.id


def test_atomic_decrements_do_not_produce_negative_counts(community):
    repo, _, solution_id = community
    assert repo.adjust_vote_count(solution_id, -1) == 0
    assert repo.adjust_favorite_count(solution_id, -1) == 0
    assert repo.adjust_comment_count(solution_id, -1) == 0


def test_stale_hide_preserves_new_solution_content(community, student_user, monkeypatch, db_session):
    repo, service, solution_id = community
    stale = repo.get_solution_by_id(solution_id)
    repo.update_solution(solution_id, title='新标题', content='新正文', language='cpp', is_official=True)
    db_session.commit()
    monkeypatch.setattr(repo, 'get_solution_by_id', lambda ignored: deepcopy(stale))
    service.hide(solution_id, student_user.id, 'student')
    current = repo.update_solution(solution_id)
    assert current.status == 'hidden'
    assert (current.title, current.content, current.language, current.is_official) == ('新标题', '新正文', 'cpp', True)


def test_stale_edit_cannot_unhide_or_revoke_official_status(community, student_user, monkeypatch, db_session):
    repo, service, solution_id = community
    stale = repo.get_solution_by_id(solution_id)
    repo.hide_solution(solution_id)
    repo.update_solution(solution_id, content='并发更新正文', is_official=True)
    db_session.commit()
    monkeypatch.setattr(repo, 'get_solution_by_id', lambda ignored: deepcopy(stale))
    updated = service.update(UpdateSolutionParams(solution_id, student_user.id, 'student', title='只改标题'))
    assert updated.title == '只改标题'
    assert updated.status == 'hidden'
    assert updated.is_official
    assert updated.content == '并发更新正文'


def test_disjoint_edits_from_same_old_snapshot_both_survive(community, student_user, monkeypatch):
    repo, service, solution_id = community
    stale = repo.get_solution_by_id(solution_id)
    monkeypatch.setattr(repo, 'get_solution_by_id', lambda ignored: deepcopy(stale))
    service.update(UpdateSolutionParams(solution_id, student_user.id, 'student', title='新标题'))
    updated = service.update(UpdateSolutionParams(solution_id, student_user.id, 'student', content='新正文'))
    assert (updated.title, updated.content) == ('新标题', '新正文')

@pytest.mark.parametrize('kind', ['like', 'favorite'])
def test_repeated_removal_using_old_relation_does_not_remove_other_users_count(
    kind, community, student_user, teacher_user, monkeypatch,
):
    repo, service, solution_id = community
    toggle = service.toggle_like if kind == 'like' else service.toggle_favorite
    lookup = repo.get_like if kind == 'like' else repo.get_favorite
    toggle(solution_id, student_user.id)
    toggle(solution_id, teacher_user.id)
    stale = lookup(solution_id, student_user.id)
    toggle(solution_id, student_user.id)
    monkeypatch.setattr(repo, 'get_like' if kind == 'like' else 'get_favorite', lambda *args: stale)
    result = toggle(solution_id, student_user.id)
    current = repo.get_solution_by_id(solution_id)
    if kind == 'like':
        assert result.liked is False and result.vote_count == 1
        assert current.vote_count == 1
        assert repo.list_likers(solution_id) == [teacher_user.id]
    else:
        assert result.favorited is False
        assert current.favorite_count == 1
        assert lookup(solution_id, teacher_user.id) is not None
