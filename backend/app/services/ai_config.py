"""AI configuration reader — DB overrides with .env fallback."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings


async def get_ai_config(db: AsyncSession, key: str, env_default: str = "") -> str:
    """Read AI config value from system_config table, falling back to .env."""
    from app.models.system_config import SystemConfig
    try:
        result = await db.execute(
            select(SystemConfig.value).where(SystemConfig.key == key)
        )
        row = result.scalar_one_or_none()
        if row:
            return row
    except Exception:
        pass
    return env_default


async def get_ai_config_int(db: AsyncSession, key: str, env_default: int) -> int:
    val = await get_ai_config(db, key, str(env_default))
    return int(val)


async def get_ai_config_float(db: AsyncSession, key: str, env_default: float) -> float:
    val = await get_ai_config(db, key, str(env_default))
    return float(val)


async def get_rag_params(db: AsyncSession) -> dict:
    """Get RAG chunking and retrieval params from config."""
    settings = get_settings()
    return {
        "top_k": await get_ai_config_int(db, "ai.rag_top_k", settings.RAG_TOP_K),
        "chunk_size": await get_ai_config_int(db, "ai.rag_chunk_size", settings.RAG_CHUNK_SIZE),
        "chunk_overlap": await get_ai_config_int(db, "ai.rag_chunk_overlap", settings.RAG_CHUNK_OVERLAP),
    }


async def get_provider_config(db: AsyncSession, provider_id: int) -> dict:
    """Load a single provider's config by ID. Raises ValueError if not found."""
    from app.models.ai_provider import AIProvider
    result = await db.execute(
        select(AIProvider).where(AIProvider.id == provider_id, AIProvider.is_enabled == True)
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise ValueError(f"AI provider {provider_id} not found or disabled")
    return {
        "api_key": provider.api_key,
        "api_base": provider.api_base,
        "model": provider.model,
        "max_tokens": provider.max_tokens,
        "temperature": provider.temperature,
    }


async def get_default_provider(db: AsyncSession) -> dict:
    """Get the default provider config, falling back to env vars."""
    from app.models.ai_provider import AIProvider

    # Try default_provider_id from system_config
    default_id_str = await get_ai_config(db, "ai.default_provider_id", "")
    if default_id_str:
        try:
            return await get_provider_config(db, int(default_id_str))
        except (ValueError, Exception):
            pass

    # Try first enabled provider
    result = await db.execute(
        select(AIProvider)
        .where(AIProvider.is_enabled == True)
        .order_by(AIProvider.sort_order, AIProvider.id)
        .limit(1)
    )
    provider = result.scalars().first()
    if provider:
        return {
            "api_key": provider.api_key,
            "api_base": provider.api_base,
            "model": provider.model,
            "max_tokens": provider.max_tokens,
            "temperature": provider.temperature,
        }

    # Fall back to env vars
    settings = get_settings()
    return {
        "api_key": settings.DEEPSEEK_API_KEY,
        "api_base": settings.DEEPSEEK_API_BASE,
        "model": settings.DEEPSEEK_MODEL,
        "max_tokens": settings.DEEPSEEK_MAX_TOKENS,
        "temperature": 0.3,
    }


async def list_providers(db: AsyncSession) -> list[dict]:
    """List all AI providers (admin view includes disabled ones)."""
    from app.models.ai_provider import AIProvider
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
