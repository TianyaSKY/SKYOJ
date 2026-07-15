import io
import os
import shutil
import zipfile
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.problem import Problem
from app.models.submission import Submission
from app.utils.auth_tools import AuthContext, get_current_auth
from app.utils.files import secure_filename
from app.utils.feature_flags import ENABLE_PLAGIARISM
from app.utils.pagination import paginate

router = APIRouter()
UPLOAD_BASE_DIR = "uploads/problems"


class ProblemBody(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    language: Optional[str] = None
    type: Optional[str] = None
    time_limit: Optional[int] = 1000
    memory_limit: Optional[int] = 128
    template_code: Optional[str] = ""


@router.post("/", status_code=201)
def create_problem(
    data: dict[str, Any],
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})

    new_problem = Problem(
        title=data.get("title"),
        content=data.get("content"),
        language=data.get("language"),
        type=data.get("type"),
        time_limit=data.get("time_limit", 1000),
        memory_limit=data.get("memory_limit", 128),
        template_code=data.get("template_code", ""),
    )
    db.add(new_problem)
    db.commit()
    db.refresh(new_problem)

    return {
        "message": "Problem created successfully",
        "problem_id": new_problem.id,
    }


@router.get("/")
def get_problems(
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Problem).order_by(Problem.id.desc())
    if page and page_size:
        problems, total, _pages = paginate(query, page=page, per_page=page_size)
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "problems": [
                {
                    "id": p.id,
                    "title": p.title,
                    "type": p.type,
                    "language": p.language,
                    "time_limit": p.time_limit,
                    "memory_limit": p.memory_limit,
                }
                for p in problems
            ],
        }

    problems = query.all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "type": p.type,
            "language": p.language,
            "time_limit": p.time_limit,
            "memory_limit": p.memory_limit,
        }
        for p in problems
    ]


@router.get("/{problem_id}")
def get_problem(problem_id: int, db: Session = Depends(get_db)):
    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail={"error": "Not found"})
    return {
        "id": problem.id,
        "title": problem.title,
        "content": problem.content,
        "type": problem.type,
        "language": problem.language,
        "time_limit": problem.time_limit,
        "memory_limit": problem.memory_limit,
        "template_code": problem.template_code,
    }


@router.put("/{problem_id}")
def update_problem(
    problem_id: int,
    data: dict[str, Any],
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})
    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail={"error": "Not found"})

    problem.title = data.get("title", problem.title)
    problem.content = data.get("content", problem.content)
    problem.language = data.get("language", problem.language)
    problem.type = data.get("type", problem.type)
    problem.time_limit = data.get("time_limit", problem.time_limit)
    problem.memory_limit = data.get("memory_limit", problem.memory_limit)
    problem.template_code = data.get("template_code", problem.template_code)

    db.commit()
    return {"message": "Problem updated successfully"}


@router.delete("/{problem_id}")
def delete_problem(
    problem_id: int,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})
    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail={"error": "Not found"})

    problem_dir = os.path.join(UPLOAD_BASE_DIR, str(problem_id))
    if os.path.exists(problem_dir):
        shutil.rmtree(problem_dir)

    db.delete(problem)
    db.commit()
    return {"message": "Problem deleted successfully"}


@router.post("/{problem_id}/upload_files")
async def upload_files(
    problem_id: int,
    file: UploadFile = File(...),
    auth: AuthContext = Depends(get_current_auth),
):
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})
    if not file.filename:
        raise HTTPException(status_code=400, detail={"error": "No selected file"})

    problem_dir = os.path.join(UPLOAD_BASE_DIR, str(problem_id))
    if os.path.exists(problem_dir):
        shutil.rmtree(problem_dir)
    os.makedirs(problem_dir)

    filename = secure_filename(file.filename)
    zip_path = os.path.join(problem_dir, filename)
    content = await file.read()
    with open(zip_path, "wb") as f:
        f.write(content)

    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(problem_dir)
        os.remove(zip_path)
        return {
            "message": f"Test cases for problem {problem_id} uploaded and extracted successfully.",
            "files": os.listdir(problem_dir),
        }
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail={"error": "Invalid zip file"})


@router.delete("/{problem_id}/test_cases")
def delete_test_cases(
    problem_id: int,
    auth: AuthContext = Depends(get_current_auth),
):
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})

    problem_dir = os.path.join(UPLOAD_BASE_DIR, str(problem_id))
    if os.path.exists(problem_dir):
        for filename in os.listdir(problem_dir):
            file_path = os.path.join(problem_dir, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        return {"message": f"All test cases for problem {problem_id} deleted."}
    raise HTTPException(
        status_code=404, detail={"error": "Test cases directory not found"}
    )


@router.get("/{problem_id}/test_cases")
def download_test_cases(
    problem_id: int,
    auth: AuthContext = Depends(get_current_auth),
):
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})

    problem_dir = os.path.join(UPLOAD_BASE_DIR, str(problem_id))
    if not os.path.exists(problem_dir) or not os.listdir(problem_dir):
        raise HTTPException(
            status_code=404, detail={"error": "No test cases found for this problem"}
        )

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(problem_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, problem_dir)
                zf.write(file_path, arcname)

    memory_file.seek(0)
    return StreamingResponse(
        memory_file,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="problem_{problem_id}_test_cases.zip"'
        },
    )


@router.post("/{problem_id}/check_plagiarism", status_code=202)
def check_problem_plagiarism(
    problem_id: int,
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

    submission_ids = [
        s.id for s in db.query(Submission).filter_by(problem_id=problem_id).all()
    ]
    if not submission_ids:
        return {"message": "No submissions found for this problem"}

    from app.services.plagiarism_service import plagiarism_service

    plagiarism_service.start_check_task(submission_ids)

    return {
        "message": f"Plagiarism check started for {len(submission_ids)} submissions.",
        "count": len(submission_ids),
    }
