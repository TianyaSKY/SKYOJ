"""持久化入口：注册全部 ORM 表与关系。"""

from app.persistence.community import ProblemSolution, ProblemSolutionComment, ProblemSolutionFavorite, ProblemSolutionLike, ProblemTag, ProblemTagMap
from app.persistence.dataset import Dataset
from app.persistence.exam import Exam, ExamProblem
from app.persistence.jobs import AiDraft, AsyncJob
from app.persistence.problem import Problem
from app.persistence.submission import DebugRun, PlagiarismReport, Submission
from app.persistence.system import AuditLog, SysDict
from app.persistence.user import SearchHistory, User, WrongBook


__all__ = [
    "AiDraft",
    "AsyncJob",
    "AuditLog",
    "Dataset",
    "DebugRun",
    "Exam",
    "ExamProblem",
    "PlagiarismReport",
    "Problem",
    "ProblemSolution",
    "ProblemSolutionComment",
    "ProblemSolutionLike",
    "ProblemTag",
    "ProblemTagMap",
    "SearchHistory",
    "Submission",
    "SysDict",
    "User",
    "WrongBook",
]
