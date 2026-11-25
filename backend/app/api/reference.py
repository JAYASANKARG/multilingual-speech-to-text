import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.schemas.reference import Language, Quota
from app.services import rate_limit
from app.stt.languages import LANGUAGES

router = APIRouter(tags=["reference"])


@router.get("/languages", operation_id="listLanguages", response_model=list[Language])
async def list_languages() -> list[Language]:
    return [Language(code=l.code, name=l.name, pinnable=l.pinnable) for l in LANGUAGES]


@router.get("/quota", operation_id="getQuota", response_model=Quota)
async def get_quota(
    request: Request, response: Response, db: Annotated[AsyncSession, Depends(get_session)]
) -> Quota:
    visitor_id = rate_limit.visitor_id_from(request)
    if visitor_id is None:
        visitor_id = str(uuid.uuid4())
        rate_limit.set_visitor_cookie(response, visitor_id)
    ip_hash = rate_limit.hash_ip(rate_limit.client_ip(request))
    return await rate_limit.quota(db, visitor_id, ip_hash)
