import csv
import hashlib
import io
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import SECRET_KEY
from app.database import get_db
from app.models.exam import Exam, ExamProblem
from app.models.submission import Submission
from app.models.user import User
from app.utils.auth_tools import AuthContext, encode_auth_token, get_current_auth
from app.utils.feature_flags import ENABLE_PLAGIARISM

router = APIRouter()


def hash_exam_password(password):
    if not password:
        return None
    return hashlib.sha256((password + SECRET_KEY).encode()).hexdigest()


@router.post("/", status_code=201)
def create_exam(
    data: dict[str, Any],
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})

    try:
        raw_password = data.get("password")
        hashed_password = hash_exam_password(raw_password) if raw_password else None
        new_exam = Exam(
            title=data["title"],
            description=data.get("description", ""),
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
            password=hashed_password,
            is_visible=data.get("is_visible", False),
            created_by=auth.user.id,
        )
        db.add(new_exam)
        db.commit()
        db.refresh(new_exam)
        return new_exam.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})


@router.get("/")
def get_exams(
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    if auth.user.role == "teacher":
        exams = db.query(Exam).all()
    else:
        exams = db.query(Exam).filter_by(is_visible=True).all()

    result = []
    for e in exams:
        d = e.to_dict()
        d["problem_count"] = (
            db.query(ExamProblem).filter_by(exam_id=e.id).count()
        )
        d["submission_count"] = (
            db.query(Submission).filter_by(exam_id=e.id).count()
        )
        result.append(d)
    return result


# Static paths MUST be registered before /{exam_id} so "status"/"exit"
# are not parsed as exam_id (which would yield 422 int_parsing).
@router.post("/exit")
def exit_exam(auth: AuthContext = Depends(get_current_auth)):
    new_token = encode_auth_token(
        user_id=auth.user.id, role=auth.user.role, exam_id=-1
    )
    return {"message": "Successfully exited exam", "token": new_token}


@router.get("/status")
def get_my_exam_status(
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    user_id = auth.user.id
    exam_id = auth.exam_id

    if exam_id == -1:
        raise HTTPException(
            status_code=400,
            detail={"error": "You are not in an active exam session"},
        )

    exam_problems = db.query(ExamProblem).filter_by(exam_id=exam_id).all()
    if not exam_problems:
        return []

    result = []
    for ep in exam_problems:
        last_submission = (
            db.query(Submission)
            .filter_by(
                exam_id=exam_id, user_id=user_id, problem_id=ep.problem_id
            )
            .order_by(Submission.created_at.desc())
            .first()
        )
        result.append(
            {
                "problem_id": ep.problem_id,
                "display_id": ep.display_id,
                "title": ep.problem.title,
                "max_score": ep.score,
                "status": last_submission.status
                if last_submission
                else "Not Attempted",
                "current_score": last_submission.score if last_submission else 0,
                "last_submitted_at": last_submission.created_at.isoformat()
                if last_submission
                else None,
            }
        )
    return result


@router.get("/{exam_id}")
def get_exam_detail(
    exam_id: int,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    exam = db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail={"error": "Not found"})
    data = exam.to_dict()
    data["has_password"] = bool(exam.password)
    problems = db.query(ExamProblem).filter_by(exam_id=exam_id).all()
    data["problems"] = [
        {
            "problem_id": p.problem_id,
            "display_id": p.display_id,
            "score": p.score,
            "title": p.problem.title,
        }
        for p in problems
    ]
    return data


@router.post("/{exam_id}/enter")
def enter_exam(
    exam_id: int,
    data: Optional[dict[str, Any]] = None,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    exam = db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail={"error": "Not found"})

    now = datetime.utcnow()
    if now < exam.start_time:
        raise HTTPException(
            status_code=403, detail={"error": "Exam has not started yet"}
        )
    if now > exam.end_time:
        raise HTTPException(
            status_code=403, detail={"error": "Exam has already ended"}
        )

    if auth.exam_id != exam_id:
        if exam.password:
            data = data or {}
            input_password = data.get("password")
            if hash_exam_password(input_password) != exam.password:
                raise HTTPException(
                    status_code=401, detail={"error": "Incorrect password"}
                )

    new_token = encode_auth_token(
        user_id=auth.user.id, role=auth.user.role, exam_id=exam_id
    )
    return {
        "message": "Successfully entered exam",
        "token": new_token,
        "exam_id": exam_id,
    }


@router.get("/{exam_id}/monitor")
def get_exam_monitor(
    exam_id: int,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})

    exam = db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail={"error": "Not found"})

    exam_problems = db.query(ExamProblem).filter_by(exam_id=exam_id).all()
    problem_headers = [
        {
            "problem_id": ep.problem_id,
            "display_id": ep.display_id,
            "max_score": ep.score,
        }
        for ep in exam_problems
    ]

    user_ids = [
        uid[0]
        for uid in db.query(Submission.user_id)
        .filter(Submission.exam_id == exam_id)
        .distinct()
        .all()
    ]

    monitor_data = []
    for uid in user_ids:
        user = db.get(User, uid)
        user_status = {
            "user_id": user.id,
            "username": user.username,
            "total_score": 0,
            "submissions": {},
        }
        for ep in exam_problems:
            last_sub = (
                db.query(Submission)
                .filter_by(exam_id=exam_id, user_id=uid, problem_id=ep.problem_id)
                .order_by(Submission.created_at.desc())
                .first()
            )
            if last_sub:
                user_status["submissions"][ep.problem_id] = {
                    "submission_id": last_sub.id,
                    "status": last_sub.status,
                    "score": last_sub.score,
                    "time": last_sub.created_at.isoformat(),
                }
                user_status["total_score"] += last_sub.score
            else:
                user_status["submissions"][ep.problem_id] = {
                    "status": "Not Attempted",
                    "score": 0,
                }
        monitor_data.append(user_status)

    monitor_data.sort(key=lambda x: x["total_score"], reverse=True)
    return {
        "exam_title": exam.title,
        "problems": problem_headers,
        "users": monitor_data,
    }


@router.get("/{exam_id}/rank")
def get_exam_rank(
    exam_id: int,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    exam = db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail={"error": "Not found"})

    exam_problems = db.query(ExamProblem).filter_by(exam_id=exam_id).all()
    problem_ids = [ep.problem_id for ep in exam_problems]

    submissions = (
        db.query(Submission)
        .filter(
            Submission.exam_id == exam_id,
            Submission.problem_id.in_(problem_ids),
        )
        .order_by(Submission.created_at.asc())
        .all()
    )

    rank_data = {}
    for sub in submissions:
        if sub.user_id not in rank_data:
            rank_data[sub.user_id] = {
                "user_id": sub.user_id,
                "username": sub.user.username,
                "solved": 0,
                "penalty": 0,
                "problems": {
                    pid: {"solved": False, "failed_attempts": 0, "time": 0}
                    for pid in problem_ids
                },
            }

        user_rank = rank_data[sub.user_id]
        prob_stats = user_rank["problems"].get(sub.problem_id)
        if not prob_stats or prob_stats["solved"]:
            continue

        if sub.status == "Accepted":
            prob_stats["solved"] = True
            time_diff = int((sub.created_at - exam.start_time).total_seconds())
            prob_stats["time"] = time_diff
            user_rank["solved"] += 1
            user_rank["penalty"] += time_diff + prob_stats["failed_attempts"] * 1200
        elif sub.status not in ["Pending", "Compile Error"]:
            prob_stats["failed_attempts"] += 1

    sorted_rank = list(rank_data.values())
    sorted_rank.sort(key=lambda x: (-x["solved"], x["penalty"]))

    return {
        "exam_title": exam.title,
        "problems": [
            {"problem_id": ep.problem_id, "display_id": ep.display_id}
            for ep in exam_problems
        ],
        "rank": sorted_rank,
    }


@router.put("/{exam_id}")
def update_exam(
    exam_id: int,
    data: dict[str, Any],
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})

    exam = db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail={"error": "Not found"})

    if "title" in data:
        exam.title = data["title"]
    if "description" in data:
        exam.description = data["description"]
    if "start_time" in data:
        exam.start_time = datetime.fromisoformat(data["start_time"])
    if "end_time" in data:
        exam.end_time = datetime.fromisoformat(data["end_time"])
    if "is_visible" in data:
        exam.is_visible = data["is_visible"]
    if "password" in data:
        raw_password = data["password"]
        exam.password = hash_exam_password(raw_password) if raw_password else None

    db.commit()
    return exam.to_dict()


@router.delete("/{exam_id}")
def delete_exam(
    exam_id: int,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})

    exam = db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail={"error": "Not found"})
    db.delete(exam)
    db.commit()
    return {"message": "Exam deleted"}


@router.post("/{exam_id}/problems", status_code=201)
def add_problem_to_exam(
    exam_id: int,
    data: dict[str, Any],
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})

    new_ep = ExamProblem(
        exam_id=exam_id,
        problem_id=data["problem_id"],
        display_id=data.get("display_id"),
        score=data.get("score", 100),
    )
    db.add(new_ep)
    db.commit()
    return {"message": "Problem added to exam"}


@router.delete("/{exam_id}/problems/{problem_id}")
def remove_problem_from_exam(
    exam_id: int,
    problem_id: int,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})

    ep = (
        db.query(ExamProblem)
        .filter_by(exam_id=exam_id, problem_id=problem_id)
        .first()
    )
    if not ep:
        raise HTTPException(status_code=404, detail={"error": "Not found"})
    db.delete(ep)
    db.commit()
    return {"message": "Problem removed from exam"}


@router.post("/{exam_id}/check_plagiarism", status_code=202)
def check_exam_plagiarism(
    exam_id: int,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})
    if not ENABLE_PLAGIARISM:
        raise HTTPException(
            status_code=503,
            detail={"error": "Plagiarism service is temporarily disabled"},
        )

    subquery = (
        db.query(
            Submission.user_id,
            Submission.problem_id,
            func.max(Submission.id).label("max_id"),
        )
        .filter(Submission.exam_id == exam_id)
        .group_by(Submission.user_id, Submission.problem_id)
        .subquery()
    )
    submission_ids = [row.max_id for row in db.query(subquery.c.max_id).all()]

    if not submission_ids:
        return {"message": "No submissions found for this exam"}

    from app.services.plagiarism_service import plagiarism_service

    plagiarism_service.start_check_task(submission_ids)
    return {
        "message": f"Plagiarism check started for {len(submission_ids)} final submissions in exam #{exam_id}.",
        "count": len(submission_ids),
    }


@router.get("/{exam_id}/export_scores")
def export_exam_scores(
    exam_id: int,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})

    exam = db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail={"error": "Not found"})

    exam_problems = (
        db.query(ExamProblem)
        .filter_by(exam_id=exam_id)
        .order_by(ExamProblem.display_id)
        .all()
    )
    user_ids = [
        uid[0]
        for uid in db.query(Submission.user_id)
        .filter(Submission.exam_id == exam_id)
        .distinct()
        .all()
    ]

    output = io.StringIO()
    writer = csv.writer(output)
    header = ["User ID", "Username"]
    for ep in exam_problems:
        header.append(f"{ep.display_id} (Max: {ep.score})")
    header.append("Total Score")
    writer.writerow(header)

    for uid in user_ids:
        user = db.get(User, uid)
        row = [user.id, user.username]
        total_score = 0
        for ep in exam_problems:
            last_sub = (
                db.query(Submission)
                .filter_by(exam_id=exam_id, user_id=uid, problem_id=ep.problem_id)
                .order_by(Submission.created_at.desc())
                .first()
            )
            score = last_sub.score if last_sub else 0
            row.append(score)
            total_score += score
        row.append(total_score)
        writer.writerow(row)

    output.seek(0)
    filename = f"exam_{exam_id}_scores_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
