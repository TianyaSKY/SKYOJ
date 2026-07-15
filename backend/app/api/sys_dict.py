import os
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.exam import Exam
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.sysdict import SysDict
from app.models.user import User
from app.utils.auth_tools import AuthContext, get_current_auth

router = APIRouter()


@router.get("/info")
def get_sys_info(db: Session = Depends(get_db)):
    dicts = db.query(SysDict).all()
    config = {d.key: d.val for d in dicts}
    config.pop("llm_api_key", None)
    config.pop("llm_api_url", None)
    config.pop("llm_model_name", None)

    required_fields = {
        "title": "SKYOJ",
        "info": "",
        "warning": "false",
        "practice": "true",
    }
    for key, default in required_fields.items():
        if key not in config:
            config[key] = default

    if "warning" in config:
        config["warning"] = str(config["warning"]).lower() == "true"
    if "practice" in config:
        config["practice"] = str(config["practice"]).lower() == "true"

    llm_api_url = os.getenv("LLM_API_URL", "").strip()
    llm_model_name = os.getenv("LLM_MODEL_NAME", "").strip()
    llm_api_key = os.getenv("LLM_API_KEY", "").strip()
    config["llm_api_url"] = llm_api_url
    config["llm_model_name"] = llm_model_name
    config["llm_env_ready"] = bool(llm_api_url and llm_model_name and llm_api_key)

    return config


@router.put("/info")
def update_sys_info(
    data: dict[str, Any],
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})
    if not data or not isinstance(data, dict):
        raise HTTPException(status_code=400, detail={"error": "Invalid data format"})

    blocked_keys = {"llm_api_key", "llm_api_url", "llm_model_name"}
    updated_keys = []
    skipped_keys = []
    for key, val in data.items():
        if key in blocked_keys:
            skipped_keys.append(key)
            continue
        item = db.query(SysDict).filter_by(key=key).first()
        stored = str(val).lower() if isinstance(val, bool) else str(val)
        if item:
            item.val = stored
        else:
            db.add(SysDict(key=key, val=stored))
        updated_keys.append(key)

    db.commit()
    return {
        "message": "System configuration updated successfully",
        "updated_keys": updated_keys,
        "skipped_keys": skipped_keys,
    }


@router.delete("/info/{key}")
def delete_sys_info(
    key: str,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})

    item = db.query(SysDict).filter_by(key=key).first()
    if not item:
        raise HTTPException(status_code=404, detail={"error": "Key not found"})

    db.delete(item)
    db.commit()
    return {"message": f"Key '{key}' deleted successfully"}


@router.get("/statistics")
def get_statistics(
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    if auth.user.role != "teacher":
        raise HTTPException(status_code=403, detail={"error": "Permission denied"})

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_submissions = (
        db.query(Submission).filter(Submission.created_at >= today_start).count()
    )
    total_problems = db.query(Problem).count()
    total_users = db.query(User).count()

    now = datetime.utcnow()
    one_year_ago = now - timedelta(days=365)
    six_months_ago = now + timedelta(days=180)
    exams_in_range = (
        db.query(Exam)
        .filter(Exam.start_time >= one_year_ago, Exam.start_time <= six_months_ago)
        .count()
    )

    return {
        "today_submissions": today_submissions,
        "total_problems": total_problems,
        "total_users": total_users,
        "exams_in_period": exams_in_range,
    }
