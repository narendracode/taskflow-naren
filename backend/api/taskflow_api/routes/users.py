from typing import Literal

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow_common.database import get_db
from taskflow_common.models import User

from ..dependencies import get_current_user
from ..schemas.auth import UserResponse

logger = structlog.get_logger()
router = APIRouter()


class UpdatePreferencesRequest(BaseModel):
    theme: Literal["light", "dark"]


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile including preferences."""
    return UserResponse.model_validate(current_user)


@router.patch("/me/preferences", response_model=UserResponse)
async def update_preferences(
    body: UpdatePreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Persist user preferences (theme) so they sync across devices."""
    current_user.theme = body.theme
    await db.flush()
    await db.refresh(current_user)
    logger.info("preferences_updated", user_id=str(current_user.id), theme=body.theme)
    return UserResponse.model_validate(current_user)
