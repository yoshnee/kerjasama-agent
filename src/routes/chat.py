from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import Business
from src.schemas import BusinessInfoResponse, ChatRequest, ChatResponse
from src.agent import ChatAgent

router = APIRouter(prefix="/chat")
limiter = Limiter(key_func=get_remote_address)

_agent: Optional[ChatAgent] = None


def get_agent() -> ChatAgent:
    global _agent
    if _agent is None:
        _agent = ChatAgent()
    return _agent


async def get_active_business(slug: str, db: AsyncSession) -> Business:
    result = await db.execute(
        select(Business).where(Business.slug == slug, Business.is_active == True)
    )
    business = result.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business


@router.get("/{slug}/info", response_model=BusinessInfoResponse)
async def get_business_info(slug: str, db: AsyncSession = Depends(get_db)):
    business = await get_active_business(slug, db)

    name_source = business.owner_name or business.business_name or "?"
    avatar_initial = name_source[0].upper()
    services = business.services if business.services else []
    has_services = isinstance(services, list) and len(services) > 0

    return BusinessInfoResponse(
        business_name=business.business_name or "",
        avatar_initial=avatar_initial,
        whatsapp_number=business.whatsapp_number,
        accent_color=business.accent_color or "#3BABCD",
        pricing_text=business.pricing_text,
        services=services if has_services else None,
        has_services=has_services,
    )


@router.post("/{slug}/message", response_model=ChatResponse)
@limiter.limit("20/minute")
async def send_message(
    request: Request,
    slug: str,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    business = await get_active_business(slug, db)
    agent = get_agent()
    history = body.history[-6:]

    result = await agent.generate_response(
        message=body.message,
        history=history,
        business=business,
        db=db,
    )
    return ChatResponse(**result)
