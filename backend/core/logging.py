"""
Merkezi loglama yapılandırması.
"""
import logging
import sys
from pathlib import Path
from backend.core.config import settings


def setup_logging() -> logging.Logger:
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    handlers = [logging.StreamHandler(sys.stdout)]

    if settings.LOG_FILE:
        log_path = Path(settings.LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )

    # Gürültülü kütüphaneleri sustur
    for noisy in ["httpx", "httpcore", "asyncio", "playwright"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return logging.getLogger("opensignal")


logger = setup_logging()
