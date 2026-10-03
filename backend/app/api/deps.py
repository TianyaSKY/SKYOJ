"""FastAPI 依赖注入。"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.clients.avatar_storage_client import AvatarStorageClient
from app.clients.dataset_storage_client import DatasetStorageClient
from app.clients.jplag_client import JPlagClient
from app.clients.llm_client import LlmClient
from app.clients.problem_test_case_storage_client import ProblemTestCaseStorageClient
from app.clients.submission_storage_client import SubmissionStorageClient
from app.persistence.database import get_db
from app.persistence.jobs import AiDraftRepository
from app.persistence.dataset import DatasetRepository
from app.persistence.submission import DebugRunRepository
from app.persistence.exam import ExamRepository
from app.persistence.submission import PlagiarismRepository
from app.persistence.problem import ProblemRepository
from app.persistence.user import SearchRepository
from app.persistence.submission import SubmissionRepository
from app.persistence.system import SystemRepository
from app.persistence.user import UserRepository
from app.services.ai_draft import AiDraftService
from app.services.async_job import AsyncJobService
from app.services.auth import AuthService
from app.services.dataset import DatasetService
from app.services.debug import DebugService
from app.services.exam import ExamService
from app.services.llm import LlmFacadeService
from app.services.plagiarism import PlagiarismService
from app.services.community import SolutionService, TagService
from app.services.problem import ProblemService
from app.services.search import SearchFacadeService
from app.services.submission import SubmissionService
from app.services.system import SystemService
from app.services.user import UserService
from app.services.wrong_book import WrongBookService


def get_ai_draft_service(db: Session = Depends(get_db)) -> AiDraftService:
    """构造 AI 草稿服务。"""
    return AiDraftService(
        draft_repository=AiDraftRepository(db),
        problem_repository=ProblemRepository(db),
        job_service=AsyncJobService.from_session(db),
        llm_client=LlmClient(),
    )


def get_problem_service(db: Session = Depends(get_db)) -> ProblemService:
    """构造题目领域服务。"""
    return ProblemService(
        problem_repository=ProblemRepository(db),
        test_case_storage=ProblemTestCaseStorageClient(),
    )


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """构造认证领域服务。"""
    return AuthService(user_repository=UserRepository(db))


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """构造用户领域服务。"""
    return UserService(UserRepository(db), AvatarStorageClient())


def get_exam_service(db: Session = Depends(get_db)) -> ExamService:
    """构造考试领域服务。"""
    return ExamService(ExamRepository(db))


def get_llm_facade_service(db: Session = Depends(get_db)) -> LlmFacadeService:
    """构造同步 LLM 功能服务。"""
    return LlmFacadeService(LlmClient(), SubmissionRepository(db))


def get_dataset_service(db: Session = Depends(get_db)) -> DatasetService:
    """构造数据集领域服务。"""
    storage_client = DatasetStorageClient()
    return DatasetService(
        dataset_repository=DatasetRepository(db),
        storage_client=storage_client,
        job_service=AsyncJobService.from_session(db),
    )


def get_submission_service(db: Session = Depends(get_db)) -> SubmissionService:
    """构造提交领域服务。"""
    return SubmissionService(
        SubmissionRepository(db),
        AsyncJobService.from_session(db),
        SubmissionStorageClient(),
    )


def get_debug_service(db: Session = Depends(get_db)) -> DebugService:
    """构造调试运行领域服务。"""
    return DebugService(DebugRunRepository(db), AsyncJobService.from_session(db))


def get_system_service(db: Session = Depends(get_db)) -> SystemService:
    """构造系统设置服务。"""
    return SystemService(SystemRepository(db))


def get_search_service(db: Session = Depends(get_db)) -> SearchFacadeService:
    """构造搜索服务。"""
    return SearchFacadeService(
        SearchRepository(db), test_case_storage=ProblemTestCaseStorageClient()
    )


def get_plagiarism_service(db: Session = Depends(get_db)) -> PlagiarismService:
    """构造查重服务。"""
    return PlagiarismService(
        plagiarism_repo=PlagiarismRepository(db),
        submission_repo=SubmissionRepository(db),
        jplag_client=JPlagClient(),
        job_service=AsyncJobService.from_session(db),
    )


def get_solution_service(db: Session = Depends(get_db)) -> SolutionService:
    """构造题解业务服务。"""
    return SolutionService(db)


def get_tag_service(db: Session = Depends(get_db)) -> TagService:
    """构造题目标签业务服务。"""
    return TagService(db)


def get_wrong_book_service(db: Session = Depends(get_db)) -> WrongBookService:
    """构造错题本服务。"""
    return WrongBookService(db)
