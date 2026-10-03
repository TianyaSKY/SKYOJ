"""冻结当前表结构，兼容空库及旧版未版本化数据库。"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "async_jobs" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "async_jobs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("task_name", sa.String(length=128), nullable=False),
            sa.Column("queue", sa.String(length=32), nullable=False),
            sa.Column("payload", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("dedupe_key", sa.String(length=255), nullable=True),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("max_attempts", sa.Integer(), nullable=False),
            sa.Column("lease_until", sa.DateTime(), nullable=True),
            sa.Column("available_at", sa.DateTime(), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("dedupe_key"),
        )
    if "problem_tags" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "problem_tags",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("slug", sa.String(length=50), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("category", sa.String(length=50), nullable=True),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("slug", name="uq_problem_tags_slug"),
        )
    if "problems" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "problems",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("type", sa.Enum("acm", "oop", "kaggle"), nullable=False),
            sa.Column(
                "language", sa.Enum("python", "java", "c", "cpp"), nullable=False
            ),
            sa.Column("time_limit", sa.Integer(), nullable=True),
            sa.Column("memory_limit", sa.Integer(), nullable=True),
            sa.Column("test_case_path", sa.String(length=500), nullable=True),
            sa.Column("template_code", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if "sys_dict" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "sys_dict",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("key", sa.String(length=100), nullable=True),
            sa.Column("val", sa.String(length=100), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if "users" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("username", sa.String(length=80), nullable=False),
            sa.Column("password_hash", sa.String(length=128), nullable=False),
            sa.Column("role", sa.Enum("student", "teacher"), nullable=True),
            sa.Column("avatar", sa.String(length=255), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("username"),
        )
    if "ai_drafts" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "ai_drafts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("task_type", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("problem_id", sa.Integer(), nullable=True),
            sa.Column("request_payload", sa.Text(), nullable=True),
            sa.Column("result_payload", sa.Text(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("consumed_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["problem_id"], ["problems.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if "audit_logs" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(length=64), nullable=False),
            sa.Column("method", sa.String(length=16), nullable=False),
            sa.Column("path", sa.String(length=255), nullable=False),
            sa.Column("status_code", sa.Integer(), nullable=True),
            sa.Column("ip", sa.String(length=64), nullable=True),
            sa.Column("user_agent", sa.String(length=255), nullable=True),
            sa.Column("payload_summary", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if "datasets" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "datasets",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("file_path", sa.String(length=256), nullable=False),
            sa.Column("file_size", sa.String(length=64), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("temp_path", sa.String(length=500), nullable=True),
            sa.Column("file_hash", sa.String(length=64), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("uploader_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["uploader_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if "exams" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "exams",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("start_time", sa.DateTime(), nullable=False),
            sa.Column("end_time", sa.DateTime(), nullable=False),
            sa.Column("contest_type", sa.String(length=10), nullable=False),
            sa.Column("freeze_minutes", sa.Integer(), nullable=True),
            sa.Column("password", sa.String(length=2000), nullable=True),
            sa.Column("is_visible", sa.Boolean(), nullable=True),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if "problem_solutions" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "problem_solutions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("problem_id", sa.Integer(), nullable=False),
            sa.Column("author_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("language", sa.String(length=50), nullable=True),
            sa.Column("is_official", sa.Boolean(), nullable=False),
            sa.Column(
                "status",
                sa.Enum(
                    "published", "hidden", "pending", name="problem_solutions_status"
                ),
                nullable=False,
            ),
            sa.Column("vote_count", sa.Integer(), nullable=False),
            sa.Column("comment_count", sa.Integer(), nullable=False),
            sa.Column("view_count", sa.Integer(), nullable=False),
            sa.Column("favorite_count", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
            sa.ForeignKeyConstraint(
                ["problem_id"], ["problems.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    if "problem_tag_maps" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "problem_tag_maps",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("problem_id", sa.Integer(), nullable=False),
            sa.Column("tag_id", sa.Integer(), nullable=False),
            sa.Column("approved", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["problem_id"], ["problems.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["tag_id"], ["problem_tags.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "problem_id", "tag_id", name="uq_problem_tag_maps_pair"
            ),
        )
    if "search_history" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "search_history",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("query", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if "debug_runs" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "debug_runs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("problem_id", sa.Integer(), nullable=False),
            sa.Column("exam_id", sa.Integer(), nullable=True),
            sa.Column("language", sa.String(length=50), nullable=False),
            sa.Column("code_content", sa.Text(), nullable=False),
            sa.Column(
                "status",
                sa.Enum(
                    "Pending",
                    "Accepted",
                    "Wrong Answer",
                    "Time Limit Exceeded",
                    "Runtime Error",
                    "Compile Error",
                    "System Error",
                ),
                nullable=False,
            ),
            sa.Column("case_name", sa.String(length=128), nullable=True),
            sa.Column("input", sa.Text(), nullable=True),
            sa.Column("expected_output", sa.Text(), nullable=True),
            sa.Column("actual_output", sa.Text(), nullable=True),
            sa.Column("error_output", sa.Text(), nullable=True),
            sa.Column("time_used_ms", sa.Integer(), nullable=True),
            sa.Column("memory_used_kb", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["exam_id"], ["exams.id"]),
            sa.ForeignKeyConstraint(
                ["problem_id"], ["problems.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if "exam_problems" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "exam_problems",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("exam_id", sa.Integer(), nullable=False),
            sa.Column("problem_id", sa.Integer(), nullable=False),
            sa.Column("display_id", sa.String(length=10), nullable=True),
            sa.Column("score", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["exam_id"], ["exams.id"]),
            sa.ForeignKeyConstraint(
                ["problem_id"], ["problems.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    if "problem_solution_comments" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "problem_solution_comments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("solution_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("content", sa.String(length=1000), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["solution_id"], ["problem_solutions.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if "problem_solution_favorites" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "problem_solution_favorites",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("solution_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["solution_id"], ["problem_solutions.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "solution_id", "user_id", name="uq_problem_solution_favorites_pair"
            ),
        )
    if "problem_solution_likes" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "problem_solution_likes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("solution_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["solution_id"], ["problem_solutions.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "solution_id", "user_id", name="uq_problem_solution_likes_pair"
            ),
        )
    if "submissions" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "submissions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("problem_id", sa.Integer(), nullable=False),
            sa.Column("exam_id", sa.Integer(), nullable=True),
            sa.Column("code_path", sa.String(length=500), nullable=True),
            sa.Column("code_content", sa.Text(), nullable=True),
            sa.Column("language", sa.String(length=50), nullable=True),
            sa.Column(
                "status",
                sa.Enum(
                    "Pending",
                    "Accepted",
                    "Wrong Answer",
                    "Time Limit Exceeded",
                    "Runtime Error",
                    "Compile Error",
                    "System Error",
                ),
                nullable=True,
            ),
            sa.Column("score", sa.Float(), nullable=True),
            sa.Column("output_log", sa.Text(), nullable=True),
            sa.Column("case_results", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["exam_id"], ["exams.id"]),
            sa.ForeignKeyConstraint(
                ["problem_id"], ["problems.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if "plagiarism_reports" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "plagiarism_reports",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("problem_id", sa.Integer(), nullable=False),
            sa.Column("submission_a_id", sa.Integer(), nullable=False),
            sa.Column("submission_b_id", sa.Integer(), nullable=False),
            sa.Column("similarity_score", sa.Float(), nullable=True),
            sa.Column("matched_blocks", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=True),
            sa.Column("jplag_result_id", sa.String(length=100), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["problem_id"], ["problems.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["submission_a_id"], ["submissions.id"]),
            sa.ForeignKeyConstraint(["submission_b_id"], ["submissions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if "wrong_books" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "wrong_books",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("problem_id", sa.Integer(), nullable=False),
            sa.Column("first_wrong_at", sa.DateTime(), nullable=False),
            sa.Column("latest_wrong_at", sa.DateTime(), nullable=False),
            sa.Column("submission_id", sa.Integer(), nullable=True),
            sa.Column("accepted", sa.Boolean(), nullable=False),
            sa.Column("reviewed", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["problem_id"], ["problems.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "user_id", "problem_id", name="uq_wrong_books_user_problem"
            ),
        )

    # 只补齐原启动脚本支持的旧列；其他 schema 差异应另建迁移。
    legacy_columns = {
        "submissions": [sa.Column("case_results", sa.JSON(), nullable=True)],
        "exams": [
            sa.Column(
                "contest_type", sa.String(10), server_default="icpc", nullable=False
            ),
            sa.Column("freeze_minutes", sa.Integer(), nullable=True),
        ],
        "datasets": [
            sa.Column("status", sa.String(32), server_default="ready", nullable=False),
            sa.Column("temp_path", sa.String(500), nullable=True),
            sa.Column("file_hash", sa.String(64), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
        ],
    }
    for table, columns in legacy_columns.items():
        existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}
        for column in columns:
            if column.name not in existing:
                op.add_column(table, column)

    # 补列之后再创建索引，兼容旧库缺少索引字段的情况。
    if "ix_async_jobs_available_at" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("async_jobs")
    }:
        op.create_index(
            op.f("ix_async_jobs_available_at"),
            "async_jobs",
            ["available_at"],
            unique=False,
        )
    if "ix_async_jobs_lease_until" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("async_jobs")
    }:
        op.create_index(
            op.f("ix_async_jobs_lease_until"),
            "async_jobs",
            ["lease_until"],
            unique=False,
        )
    if "ix_async_jobs_status" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("async_jobs")
    }:
        op.create_index(
            op.f("ix_async_jobs_status"), "async_jobs", ["status"], unique=False
        )
    if "ix_async_jobs_status_available" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("async_jobs")
    }:
        op.create_index(
            "ix_async_jobs_status_available",
            "async_jobs",
            ["status", "available_at"],
            unique=False,
        )
    if "ix_problem_tags_category" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("problem_tags")
    }:
        op.create_index(
            "ix_problem_tags_category", "problem_tags", ["category"], unique=False
        )
    if "ix_ai_drafts_status" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("ai_drafts")
    }:
        op.create_index(
            op.f("ix_ai_drafts_status"), "ai_drafts", ["status"], unique=False
        )
    if "ix_ai_drafts_task_type" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("ai_drafts")
    }:
        op.create_index(
            op.f("ix_ai_drafts_task_type"), "ai_drafts", ["task_type"], unique=False
        )
    if "ix_ai_drafts_user_id" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("ai_drafts")
    }:
        op.create_index(
            op.f("ix_ai_drafts_user_id"), "ai_drafts", ["user_id"], unique=False
        )
    if "ix_datasets_status" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("datasets")
    }:
        op.create_index(
            op.f("ix_datasets_status"), "datasets", ["status"], unique=False
        )
    if "ix_problem_solutions_author" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("problem_solutions")
    }:
        op.create_index(
            "ix_problem_solutions_author",
            "problem_solutions",
            ["author_id"],
            unique=False,
        )
    if "ix_problem_solutions_problem" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("problem_solutions")
    }:
        op.create_index(
            "ix_problem_solutions_problem",
            "problem_solutions",
            ["problem_id"],
            unique=False,
        )
    if "ix_problem_solutions_problem_status" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("problem_solutions")
    }:
        op.create_index(
            "ix_problem_solutions_problem_status",
            "problem_solutions",
            ["problem_id", "status", "is_official", "vote_count"],
            unique=False,
        )
    if "ix_problem_tag_maps_problem" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("problem_tag_maps")
    }:
        op.create_index(
            "ix_problem_tag_maps_problem",
            "problem_tag_maps",
            ["problem_id"],
            unique=False,
        )
    if "ix_problem_tag_maps_tag" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("problem_tag_maps")
    }:
        op.create_index(
            "ix_problem_tag_maps_tag", "problem_tag_maps", ["tag_id"], unique=False
        )
    if "ix_debug_runs_problem_created" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("debug_runs")
    }:
        op.create_index(
            "ix_debug_runs_problem_created",
            "debug_runs",
            ["problem_id", "created_at"],
            unique=False,
        )
    if "ix_debug_runs_user_created" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("debug_runs")
    }:
        op.create_index(
            "ix_debug_runs_user_created",
            "debug_runs",
            ["user_id", "created_at"],
            unique=False,
        )
    if "ix_exam_problems_exam_id" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("exam_problems")
    }:
        op.create_index(
            "ix_exam_problems_exam_id", "exam_problems", ["exam_id"], unique=False
        )
    if "ix_problem_solution_comments_solution" not in {
        i["name"]
        for i in sa.inspect(op.get_bind()).get_indexes("problem_solution_comments")
    }:
        op.create_index(
            "ix_problem_solution_comments_solution",
            "problem_solution_comments",
            ["solution_id"],
            unique=False,
        )
    if "ix_problem_solution_favorites_user" not in {
        i["name"]
        for i in sa.inspect(op.get_bind()).get_indexes("problem_solution_favorites")
    }:
        op.create_index(
            "ix_problem_solution_favorites_user",
            "problem_solution_favorites",
            ["user_id"],
            unique=False,
        )
    if "ix_problem_solution_likes_user" not in {
        i["name"]
        for i in sa.inspect(op.get_bind()).get_indexes("problem_solution_likes")
    }:
        op.create_index(
            "ix_problem_solution_likes_user",
            "problem_solution_likes",
            ["user_id"],
            unique=False,
        )
    if "ix_submissions_created_at" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("submissions")
    }:
        op.create_index(
            "ix_submissions_created_at", "submissions", ["created_at"], unique=False
        )
    if "ix_submissions_exam_problem_user" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("submissions")
    }:
        op.create_index(
            "ix_submissions_exam_problem_user",
            "submissions",
            ["exam_id", "problem_id", "user_id"],
            unique=False,
        )
    if "ix_plagiarism_pair" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("plagiarism_reports")
    }:
        op.create_index(
            "ix_plagiarism_pair",
            "plagiarism_reports",
            ["problem_id", "submission_a_id", "submission_b_id"],
            unique=True,
        )
    if "ix_wrong_books_accepted" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("wrong_books")
    }:
        op.create_index(
            "ix_wrong_books_accepted", "wrong_books", ["accepted"], unique=False
        )
    if "ix_wrong_books_problem" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("wrong_books")
    }:
        op.create_index(
            "ix_wrong_books_problem", "wrong_books", ["problem_id"], unique=False
        )
    if "ix_wrong_books_user" not in {
        i["name"] for i in sa.inspect(op.get_bind()).get_indexes("wrong_books")
    }:
        op.create_index("ix_wrong_books_user", "wrong_books", ["user_id"], unique=False)


def downgrade() -> None:
    # 初始版本会接管已有生产表，禁止自动删除，避免误删历史数据。
    raise RuntimeError("初始迁移不支持自动降级；请从已验证的备份恢复")
