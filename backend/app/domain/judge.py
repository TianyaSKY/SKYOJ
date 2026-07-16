"""判题相关业务参数与结果。"""

from dataclasses import dataclass
from typing import Optional


# 提交状态常量
STATUS_PENDING = "Pending"
STATUS_ACCEPTED = "Accepted"
STATUS_WRONG_ANSWER = "Wrong Answer"
STATUS_TIME_LIMIT_EXCEEDED = "Time Limit Exceeded"
STATUS_RUNTIME_ERROR = "Runtime Error"
STATUS_COMPILE_ERROR = "Compile Error"
STATUS_SYSTEM_ERROR = "System Error"


# 题目类型常量
PROBLEM_TYPE_ACM = "acm"
PROBLEM_TYPE_OOP = "oop"
PROBLEM_TYPE_KAGGLE = "kaggle"


# 编程语言常量
LANGUAGE_PYTHON = "python"
LANGUAGE_JAVA = "java"
LANGUAGE_C = "c"
LANGUAGE_CPP = "cpp"


@dataclass(frozen=True)
class JudgeParams:
    """判题参数。"""

    submission_id: int
    problem_type: str
    user_code: str
    problem_id: int
    language: str
    time_limit: int = 1000
    memory_limit: int = 128


@dataclass(frozen=True)
class JudgeResult:
    """判题结果。"""

    status: str
    score: float
    log: str


@dataclass(frozen=True)
class LangConfig:
    """语言编译运行配置。"""

    src: str
    compile: Optional[str]
    run: str


@dataclass(frozen=True)
class SaveScriptParams:
    """保存非 ACM 评测脚本参数。"""

    problem_id: int
    code: str
    problem_type: str
    language: str


@dataclass(frozen=True)
class SaveScriptResult:
    """保存脚本结果。"""

    success: bool
    message: str
