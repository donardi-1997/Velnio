from fastapi import APIRouter, Depends

from app.api.deps import get_current_workspace
from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceResponse

router = APIRouter()


@router.get("", response_model=WorkspaceResponse)
async def get_workspace(workspace: Workspace = Depends(get_current_workspace)):
    return workspace
