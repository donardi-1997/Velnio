from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    owner_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class WorkspaceMemberResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: str

    class Config:
        from_attributes = True
