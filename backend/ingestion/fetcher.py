"""
HTTP içerik çekme modülü.
Retry, timeout ve rate limiting içerir.
"""
import asyncio
import logging
import random
from typing import Optional, Tuple
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Farklı User-Agent'lar - basit anti-bot bypass
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    settings.USER_AGENT,
]


def _get_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "DNT": "1",
    }


async def fetch_url_async(
    url: str,
    timeout: int = None,
) -> Tuple[Optional[str], int]:
    """
    URL'yi asenkron olarak çek.
    (içerik, status_code) döndür.
    """
    if timeout is None:
        timeout = settings.REQUEST_TIMEOUT_SECONDS

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers=_get_headers(),
            verify=False,  # SSL hatalarını atla
        ) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.text, response.status_code
            else:
                logger.warning(f"HTTP {response.status_code} for {url}")
                return None, response.status_code
    except httpx.TimeoutException:
        logger.warning(f"Timeout: {url}")
        return None, 408
    except Exception as e:
        logger.error(f"Fetch hatası {url}: {e}")
        return None, 0


def fetch_url_sync(
    url: str,
    timeout: int = None,
) -> Tuple[Optional[str], int]:
    """
    URL'yi senkron olarak çek.
    (içerik, status_code) döndür.
    """
    if timeout is None:
        timeout = settings.REQUEST_TIMEOUT_SECONDS

    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=timeout,
            headers=_get_headers(),
            verify=False,
        ) as client:
            response = client.get(url)
            if response.status_code == 200:
                return response.text, response.status_code
            else:
                logger.warning(f"HTTP {response.status_code} for {url}")
                return None, response.status_code
    except httpx.TimeoutException:
        logger.warning(f"Timeout: {url}")
        return None, 408
    except Exception as e:
        logger.error(f"Fetch hatası {url}: {e}")
        return None, 0
