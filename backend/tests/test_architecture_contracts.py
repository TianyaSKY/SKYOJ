"""检查已收紧的分层边界，避免继续引入无约束业务契约。"""

import ast
from pathlib import Path

APP = Path(__file__).parents[1] / "app"


def test_repositories_do_not_commit_or_rollback():
    for path in (APP / "persistence").glob("*.py"):
        tree = ast.parse(path.read_text())
        forbidden = [
            node.lineno
            for repository in tree.body
            if isinstance(repository, ast.ClassDef) and repository.name.endswith("Repository")
            for node in ast.walk(repository)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"commit", "rollback"}
        ]
        assert not forbidden, f"{path.name}: 事务应由 Service/UoW 控制：{forbidden}"


def test_reviewed_services_do_not_reach_into_database():
    for name in (
        "submission",
        "llm",
        "plagiarism",
        "ai_draft",
        "system",
        "problem",
        "debug",
        "dataset",
    ):
        tree = ast.parse((APP / "services" / f"{name}.py").read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith(
                    ("app.persistence.database", "app.models")
                ), name
            if isinstance(node, ast.Attribute):
                assert node.attr not in {"_db", "query"}, name


def test_service_public_dict_results_are_limited_to_json_boundary():
    for path in (APP / "services").glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in (
            method
            for service in tree.body
            if isinstance(service, ast.ClassDef) and service.name.endswith("Service")
            for method in service.body
        ):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name.startswith("_") or node.returns is None:
                continue
            # 任务 JSON 解析是序列化边界，允许字典；业务结果必须为明确 DTO。
            if path.stem == "async_job" and node.name == "parse_payload":
                continue
            annotation = ast.unparse(node.returns)
            assert "dict" not in annotation and "Dict" not in annotation, (
                path.name,
                node.name,
            )


def test_http_routes_declare_response_contracts():
    for path in (APP / "api").glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in (
            method
            for service in tree.body
            if isinstance(service, ast.ClassDef) and service.name.endswith("Service")
            for method in service.body
        ):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Attribute)
                    and isinstance(decorator.func.value, ast.Name)
                    and decorator.func.value.id.endswith("router")
                    and decorator.func.attr in {"get", "post", "put", "delete", "patch"}
                ):
                    # 文件与 SSE 接口明确使用 response_model=None。
                    assert any(k.arg == "response_model" for k in decorator.keywords), (
                        path.name,
                        node.name,
                    )
