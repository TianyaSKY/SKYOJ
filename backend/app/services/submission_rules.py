"""提交与调试共用的题型、语言业务约束。"""

from app.core.errors import InvalidStateError
from app.persistence.problem import ProblemRecord


SUPPORTED_LANGUAGES = frozenset({'python', 'java', 'c', 'cpp'})


def validate_submission_language(
    problem: ProblemRecord, language: str, *, is_file_upload: bool = False
) -> None:
    """题目允许语言是业务规则，不能只依赖前端下拉框限制。"""
    problem_type = (problem.type or 'acm').lower()
    if problem_type == 'kaggle':
        if language != 'csv':
            raise InvalidStateError('Kaggle 题目仅接受 CSV 提交')
        return
    if problem_type not in {'acm', 'oop'}:
        raise InvalidStateError('不支持的题目类型')
    if is_file_upload:
        raise InvalidStateError('该题目需要提交源代码，不能提交 CSV 附件')
    if language not in SUPPORTED_LANGUAGES:
        raise InvalidStateError('不支持的编程语言')
    allowed = {
        item.strip().lower()
        for item in (problem.language or '').split(',')
        if item.strip()
    }
    if allowed and language not in allowed:
        raise InvalidStateError('该题目不允许使用此编程语言')
