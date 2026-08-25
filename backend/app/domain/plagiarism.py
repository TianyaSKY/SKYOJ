"""查重相关业务参数与结果。"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PlagiarismScanParams:
    problem_id: int
    min_similarity: float = 0.3


@dataclass(frozen=True)
class MatchedBlock:
    start_a: int
    end_a: int
    start_b: int
    end_b: int
    code_a: str
    code_b: str


@dataclass(frozen=True)
class SimilarityPair:
    submission_a_id: int
    submission_b_id: int
    score: float
    matched_blocks: list[MatchedBlock]


@dataclass(frozen=True)
class PlagiarismResult:
    problem_id: int
    total_pairs: int
    high_risk_pairs: list[SimilarityPair]
