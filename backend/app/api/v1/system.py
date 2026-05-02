"""System configuration API — admin only."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, check_permission
from app.core.permissions import Permission
from app.models.user import User
from app.models.system_config import SystemConfig
from app.models.ai_provider import AIProvider

router = APIRouter()


# ── RAG config ───────────────────────────────────────────────────

RAG_CONFIG_DEFAULTS: dict[str, dict] = {
    "ai.rag_top_k":         {"value": "5",    "desc": "RAG 检索片段数"},
    "ai.rag_chunk_size":    {"value": "500",  "desc": "文档分块大小"},
    "ai.rag_chunk_overlap": {"value": "50",   "desc": "分块重叠大小"},
    "ai.default_provider_id": {"value": "",   "desc": "默认 AI 供应商 ID"},
}

RAG_CONFIG_KEYS = list(RAG_CONFIG_DEFAULTS.keys())


class AIConfigItem(BaseModel):
    key: str
    value: str
    description: str | None = None


class AIConfigUpdate(BaseModel):
    items: list[AIConfigItem]


async def _get_rag_config(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.key.in_(RAG_CONFIG_KEYS))
    )
    stored = {row.key: row.value for row in result.scalars().all()}

    items = []
    for key in RAG_CONFIG_KEYS:
        default = RAG_CONFIG_DEFAULTS[key]
        items.append({
            "key": key,
            "value": stored.get(key, default["value"]),
            "description": default["desc"],
        })
    return items


# ── Provider schemas ─────────────────────────────────────────────

class ProviderCreate(BaseModel):
    name: str
    provider_type: str = "custom"
    api_base: str
    api_key: str = ""
    model: str
    max_tokens: int = 4096
    temperature: float = 0.3
    is_enabled: bool = True
    sort_order: int = 0


class ProviderUpdate(BaseModel):
    name: str | None = None
    provider_type: str | None = None
    api_base: str | None = None
    api_key: str | None = None
    model: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    is_enabled: bool | None = None
    sort_order: int | None = None


# ── RAG config routes ────────────────────────────────────────────

@router.get("/ai-config")
async def get_ai_config(
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permission(Permission.ADMIN_USER_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Get RAG configuration."""
    return {"items": await _get_rag_config(db)}


@router.put("/ai-config")
async def update_ai_config(
    data: AIConfigUpdate,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permission(Permission.ADMIN_USER_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Update RAG configuration."""
    valid_keys = set(RAG_CONFIG_KEYS)
    for item in data.items:
        if item.key not in valid_keys:
            continue
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.key == item.key)
        )
        existing = result.scalars().first()
        if existing:
            existing.value = item.value
        else:
            db.add(SystemConfig(
                key=item.key,
                value=item.value,
                description=RAG_CONFIG_DEFAULTS[item.key]["desc"],
            ))
    await db.commit()
    return {"detail": "Config updated", "items": await _get_rag_config(db)}


# ── Provider CRUD routes ─────────────────────────────────────────

@router.get("/ai-providers")
async def get_ai_providers(
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permission(Permission.ADMIN_USER_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """List all AI providers."""
    result = await db.execute(
        select(AIProvider).order_by(AIProvider.sort_order, AIProvider.id)
    )
    providers = result.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "provider_type": p.provider_type,
            "api_base": p.api_base,
            "api_key": p.api_key,
            "model": p.model,
            "max_tokens": p.max_tokens,
            "temperature": p.temperature,
            "is_enabled": p.is_enabled,
            "sort_order": p.sort_order,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }
        for p in providers
    ]


@router.post("/ai-providers")
async def create_ai_provider(
    data: ProviderCreate,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permission(Permission.ADMIN_USER_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new AI provider."""
    provider = AIProvider(
        name=data.name,
        provider_type=data.provider_type,
        api_base=data.api_base,
        api_key=data.api_key,
        model=data.model,
        max_tokens=data.max_tokens,
        temperature=data.temperature,
        is_enabled=data.is_enabled,
        sort_order=data.sort_order,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return {"detail": "Provider created", "id": provider.id}


@router.put("/ai-providers/{provider_id}")
async def update_ai_provider(
    provider_id: int,
    data: ProviderUpdate,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permission(Permission.ADMIN_USER_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Update an AI provider."""
    result = await db.execute(
        select(AIProvider).where(AIProvider.id == provider_id)
    )
    provider = result.scalars().first()
    if not provider:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("AI provider not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(provider, field, value)
    await db.commit()
    return {"detail": "Provider updated"}


@router.delete("/ai-providers/{provider_id}")
async def delete_ai_provider(
    provider_id: int,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permission(Permission.ADMIN_USER_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Delete an AI provider."""
    result = await db.execute(
        delete(AIProvider).where(AIProvider.id == provider_id)
    )
    if result.rowcount == 0:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("AI provider not found")
    await db.commit()
    return {"detail": "Provider deleted"}
