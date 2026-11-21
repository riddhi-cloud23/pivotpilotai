from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.models import UserWorkspace
from backend.app.security import require_user

router = APIRouter(prefix="/workspace", tags=["workspace"])


class WorkspaceDocument(BaseModel):
    model_config = ConfigDict(extra="allow")
    version: int = Field(default=1, ge=1)
    name: str = ""
    target: str = ""
    resume: str = ""
    jd: str = ""
    apps: list[dict[str, Any]] = Field(default_factory=list)
    completed: dict[str, bool] = Field(default_factory=dict)
    milestones: dict[str, bool] = Field(default_factory=dict)


@router.get("", response_model=WorkspaceDocument)
def get_workspace(user_id: str = Depends(require_user), db: Session = Depends(get_db)) -> WorkspaceDocument:
    row = db.get(UserWorkspace, user_id)
    return WorkspaceDocument.model_validate(row.workspace if row else {"version": 1})


@router.put("", response_model=WorkspaceDocument)
def put_workspace(
    document: WorkspaceDocument,
    user_id: str = Depends(require_user),
    db: Session = Depends(get_db),
) -> WorkspaceDocument:
    row = db.get(UserWorkspace, user_id)
    clean = document.model_dump(mode="json")
    if row:
        row.workspace = clean
    else:
        row = UserWorkspace(user_id=user_id, workspace=clean)
        db.add(row)
    try:
        db.commit()
        db.refresh(row)
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="Workspace could not be saved.") from error
    return WorkspaceDocument.model_validate(row.workspace)
