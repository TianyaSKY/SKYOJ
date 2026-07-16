"""FastAPI 依赖注入。"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.clients.llm_client import LlmClient
from app.clients.avatar_storage_client import AvatarStorageClient
from app.clients.problem_test_case_storage_client import ProblemTestCaseStorageClient
from app.clients.submission_storage_client import SubmissionStorageClient
from app.clients.dataset_storage_client import DatasetStorageClient
from app.database import get_db
from app.repositories.ai_draft_repository import AiDraftRepository
from app.repositories.problem_repository import ProblemRepository
from app.repositories.user_repository import UserRepository
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.submission_repository import SubmissionRepository
from app.repositories.system_repository import SystemRepository
from app.repositories.search_repository import SearchRepository
from app.repositories.exam_repository import ExamRepository
from app.repositories.plagiarism_repository import PlagiarismRepository
from app.services.ai_draft_service import AiDraftService
from app.services.auth_service import AuthService
from app.services.problem_service import ProblemService
from app.services.dataset_service import DatasetService
from app.services.submission_service import SubmissionService
from app.services.system_service import SystemService
from app.services.search_facade_service import SearchFacadeService
from app.services.user_service import UserService
from app.services.exam_service import ExamService
from app.services.plagiarism_facade_service import PlagiarismFacadeService
from app.services.llm_facade_service import LlmFacadeService
from app.tasks.dataset_file_task import DatasetFileTask
from app.tasks.queue import get_task_queue


def get_ai_draft_service(db: Session = Depends(get_db)) -> AiDraftService:
    """构造 AI 草稿服务。"""
    return AiDraftService(
        draft_repository=AiDraftRepository(db),
        problem_repository=ProblemRepository(db),
        task_queue=get_task_queue(),
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


def get_plagiarism_service(
    db: Session = Depends(get_db),
) -> PlagiarismFacadeService:
    """构造剽窃检测领域服务。"""
    from app.services.plagiarism_service import plagiarism_service
    from app.utils.feature_flags import ENABLE_PLAGIARISM
    return PlagiarismFacadeService(
        PlagiarismRepository(db), plagiarism_service, ENABLE_PLAGIARISM
    )


def get_llm_facade_service() -> LlmFacadeService:
    """构造同步 LLM 功能服务。"""
    return LlmFacadeService(LlmClient())


def get_dataset_service(db: Session = Depends(get_db)) -> DatasetService:
    """构造数据集领域服务。"""
    storage_client = DatasetStorageClient()
    return DatasetService(
        dataset_repository=DatasetRepository(db),
        storage_client=storage_client,
        file_task=DatasetFileTask(storage_client),
    )


def get_submission_service(db: Session = Depends(get_db)) -> SubmissionService:
    """构造提交领域服务。"""
    return SubmissionService(
        SubmissionRepository(db), get_task_queue(), SubmissionStorageClient()
    )


def get_system_service(db: Session = Depends(get_db)) -> SystemService:
    """构造系统设置服务。"""
    return SystemService(SystemRepository(db))


def get_search_service(db: Session = Depends(get_db)) -> SearchFacadeService:
    """构造搜索服务。"""
    from app.services.search_service import search_service
    return SearchFacadeService(SearchRepository(db), search_service)
