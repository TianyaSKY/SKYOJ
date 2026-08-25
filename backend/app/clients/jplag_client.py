"""JPlag HTTP API 客户端。"""

import os
import time
from dataclasses import dataclass

import requests
from loguru import logger

from app.domain.plagiarism import MatchedBlock, SimilarityPair

JPLAG_BASE_URL = os.getenv("JPLAG_URL", "http://localhost:25678")
JPLAG_TIMEOUT = int(os.getenv("JPLAG_TIMEOUT", "120"))

LANGUAGE_MAP = {
    "python": "python3",
    "py": "python3",
    "java": "java",
    "c": "c",
    "cpp": "cpp",
    "c++": "cpp",
    "go": "go",
    "rust": "rust",
    "javascript": "javascript",
    "js": "javascript",
    "typescript": "typescript",
    "ts": "typescript",
}


@dataclass
class _SubmissionFile:
    name: str
    data: str


class JPlagAPIError(Exception):
    pass


class JPlagClient:
    def compare(
        self,
        submissions: list[dict],
        language: str | None = None,
        base_code: str | None = None,
        min_match_length: int = 8,
    ) -> list[SimilarityPair]:
        """向 JPlag 提交比对任务，等待完成并返回相似对列表。"""
        if len(submissions) < 2:
            return []

        resolved_lang = self._resolve_language(language, submissions)
        if resolved_lang is None:
            logger.warning("JPlag: 无法识别语言 {}，跳过查重", language)
            return []

        payload: dict = {
            "language": resolved_lang,
            "files": [
                {"name": f"sub_{s['id']}.py", "data": s["code"]}
                for s in submissions
            ],
            "submission-title-mapping": {
                f"sub_{s['id']}.py": str(s["id"]) for s in submissions
            },
            "basecode": {"files": [{"name": "base.py", "data": base_code}]} if base_code else None,
            "parameters": {
                "minimum-match-length": min_match_length,
                "maximum-gap": 3,
            },
        }
        payload["files"] = [f for f in payload["files"] if f["data"].strip()]

        try:
            resp = requests.post(
                f"{JPLAG_BASE_URL}/api/run",
                json=payload,
                timeout=JPLAG_TIMEOUT,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise JPlagAPIError(f"JPlag API 调用失败: {exc}") from exc

        result_id = resp.json().get("id")
        if not result_id:
            raise JPlagAPIError(f"JPlag 未返回 result_id: {resp.text}")

        return self._poll_result(result_id, submissions)

    def _resolve_language(
        self, language: str | None, submissions: list[dict]
    ) -> str | None:
        if language:
            lang = language.lower()
            if lang in LANGUAGE_MAP:
                return LANGUAGE_MAP[lang]
            return lang
        ext = submissions[0].get("filename", "main.py")
        _, dot_ext = ext.rsplit(".", 1) if "." in ext else ("", "py")
        return LANGUAGE_MAP.get(dot_ext.lower(), "python3")

    def _poll_result(self, result_id: str, submissions: list[dict]) -> list[SimilarityPair]:
        max_wait = JPLAG_TIMEOUT
        interval = 2
        elapsed = 0
        while elapsed < max_wait:
            try:
                resp = requests.get(
                    f"{JPLAG_BASE_URL}/api/result/{result_id}",
                    timeout=10,
                )
                resp.raise_for_status()
            except requests.RequestException as exc:
                raise JPlagAPIError(f"查询 JPlag 结果失败: {exc}") from exc

            data = resp.json()
            status = data.get("status", "").lower()
            if status == "error":
                raise JPlagAPIError(f"JPlag 比对出错: {data.get('message', '')}")
            if status == "completed":
                return self._parse_matches(data, submissions)
            logger.debug("JPlag 比对中... result_id={} status={}", result_id, status)
            time.sleep(interval)
            elapsed += interval
        raise JPlagAPIError(f"JPlag 比对超时（>{max_wait}s），result_id={result_id}")

    def _parse_matches(
        self, data: dict, submissions: list[dict]
    ) -> list[SimilarityPair]:
        pairs: list[SimilarityPair] = []
        submission_ids = {f"sub_{s['id']}.py": s["id"] for s in submissions}
        id_to_code = {s["id"]: s["code"] for s in submissions}

        for match in data.get("matches", []):
            m = match.get("match", match)
            s1_name = m.get("submission1_id") or m.get("first_submission")
            s2_name = m.get("submission2_id") or m.get("second_submission")
            if not s1_name or not s2_name:
                continue

            s1_id = submission_ids.get(s1_name)
            s2_id = submission_ids.get(s2_name)
            if s1_id is None or s2_id is None:
                continue
            if s1_id == s2_id:
                continue

            similarity = match.get("similarity", 0.0)
            raw_blocks = match.get("submatches", match.get("blocks", []))

            blocks: list[MatchedBlock] = []
            for rb in raw_blocks:
                sa, ea = rb.get("start_in_submission_a", 0), rb.get("end_in_submission_a", 0)
                sb, eb = rb.get("start_in_submission_b", 0), rb.get("end_in_submission_b", 0)
                blocks.append(
                    MatchedBlock(
                        start_a=sa, end_a=ea,
                        start_b=sb, end_b=eb,
                        code_a=self._extract_lines(id_to_code.get(s1_id, ""), sa, ea),
                        code_b=self._extract_lines(id_to_code.get(s2_id, ""), sb, eb),
                    )
                )

            pairs.append(
                SimilarityPair(
                    submission_a_id=min(s1_id, s2_id),
                    submission_b_id=max(s1_id, s2_id),
                    score=float(similarity),
                    matched_blocks=blocks,
                )
            )
        return pairs

    @staticmethod
    def _extract_lines(code: str, start: int, end: int) -> str:
        lines = code.splitlines()
        start_idx = max(0, start - 1)
        end_idx = min(len(lines), end)
        return "\n".join(lines[start_idx:end_idx])
