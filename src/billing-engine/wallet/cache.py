# Implements: work-contracts/WC-026-wbe-s2-wallet-engine.md WC026-03
# constitutional_basis: C-023, C-059, C-063
from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

import redis.asyncio

from billing_engine.config import Settings

logger = logging.getLogger(__name__)

WALLET_BALANCE_KEY_PREFIX = "wallet"
CACHE_KEY_SEPARATOR = ":"


def _build_balance_cache_key(wallet_id: UUID) -> str:
    """
    Construct Redis cache key for wallet balance.
    Pattern: wallet:{wallet_id}:balance
    """
    return f"{WALLET_BALANCE_KEY_PREFIX}{CACHE_KEY_SEPARATOR}{wallet_id}{CACHE_KEY_SEPARATOR}balance"


async def get_balance_cached(
    redis_client: redis.asyncio.Redis,
    wallet_id: UUID,
    settings: Settings,
) -> dict[str, Any] | None:
    """
    Retrieve cached wallet balance from Redis (≤50ms p99 SLA per C-091).

    Args:
        redis_client: redis.asyncio.Redis instance
        wallet_id: UUID of wallet
        settings: Settings with thread_catalog_cache_ttl_seconds

    Returns:
        Deserialized balance dict on cache hit, None on miss.
        Dict structure: {"bucket_id": str, "thread_type": str, "quantity_paise": int, "reserved_paise": int}

    Raises:
        Logs errors but does NOT raise — cache miss is acceptable (fallback to DB).
    """
    key = _build_balance_cache_key(wallet_id)

    try:
        cached_json: str | None = await redis_client.get(key)
        if cached_json is None:
            logger.debug("Cache miss for wallet_id=%s", wallet_id)
            return None

        balance_data = json.loads(cached_json)
        logger.debug("Cache hit for wallet_id=%s", wallet_id)
        return balance_data

    except (json.JSONDecodeError, TypeError):
        logger.error(
            "Failed to deserialize cached balance for wallet_id=%s",
            wallet_id,
            exc_info=True,
            extra={"wallet_id": str(wallet_id)},
        )
        # Cache corruption — invalidate and return None to trigger DB fallback
        await invalidate_wallet(redis_client, wallet_id)
        return None

    except Exception:
        logger.error(
            "Redis read error for wallet_id=%s",
            wallet_id,
            exc_info=True,
            extra={"wallet_id": str(wallet_id)},
        )
        # Redis unavailable — return None to trigger DB fallback
        return None


async def set_balance_cached(
    redis_client: redis.asyncio.Redis,
    wallet_id: UUID,
    balance_data: dict[str, Any],
    settings: Settings,
) -> None:
    """
    Write-through: store wallet balance in Redis cache.

    Args:
        redis_client: redis.asyncio.Redis instance
        wallet_id: UUID of wallet
        balance_data: dict with bucket balance state
        settings: Settings with thread_catalog_cache_ttl_seconds (TTL)

    Raises:
        Logs errors but does NOT raise — cache write failure is non-blocking (C-023).
    """
    key = _build_balance_cache_key(wallet_id)
    ttl_seconds = settings.thread_catalog_cache_ttl_seconds

    try:
        json_str = json.dumps(balance_data)
        await redis_client.set(key, json_str, ex=ttl_seconds)
        logger.debug("Cache write for wallet_id=%s", wallet_id)

    except (json.JSONEncodeError, TypeError):
        logger.error(
            "Failed to serialize balance data for wallet_id=%s",
            wallet_id,
            exc_info=True,
            extra={"wallet_id": str(wallet_id)},
        )

    except Exception:
        logger.error(
            "Redis write error for wallet_id=%s",
            wallet_id,
            exc_info=True,
            extra={"wallet_id": str(wallet_id)},
        )


async def invalidate_wallet(
    redis_client: redis.asyncio.Redis,
    wallet_id: UUID,
) -> None:
    """
    Invalidate all cache entries for a wallet (write-through on release/renew).

    Args:
        redis_client: redis.asyncio.Redis instance
        wallet_id: UUID of wallet to invalidate

    Raises:
        Logs errors but does NOT raise — invalidation failure is non-blocking.
    """
    key = _build_balance_cache_key(wallet_id)

    try:
        await redis_client.delete(key)
        logger.debug("Cache invalidated for wallet_id=%s", wallet_id)

    except Exception:
        logger.error(
            "Redis delete error for wallet_id=%s",
            wallet_id,
            exc_info=True,
            extra={"wallet_id": str(wallet_id)},
        )