"""
Uygulama konfigürasyonu.
Tüm ayarlar burada merkezi olarak yönetilir.
"""
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # Uygulama
    APP_NAME: str = "OpenSignal Radar TR"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Veritabanı
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/data/opensignal.db"

    # Sunucu
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Zamanlama - saat cinsinden
    INGESTION_INTERVAL_HOURS: float = 2.0
    SIGNAL_PROCESSING_INTERVAL_HOURS: float = 2.5
    TREND_CLUSTER_INTERVAL_HOURS: float = 6.0

    # Scraping
    REQUEST_TIMEOUT_SECONDS: int = 30
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: float = 2.0
    USER_AGENT: str = (
        "Mozilla/5.0 (compatible; OpenSignalRadar/1.0; "
        "+https://github.com/opensignal-radar)"
    )
    MAX_ARTICLES_PER_SOURCE: int = 50

    # Sinyal skorlama eşikleri
    HIGH_CONFIDENCE_THRESHOLD: float = 0.70
    MEDIUM_CONFIDENCE_THRESHOLD: float = 0.40
    HIGH_IMPACT_THRESHOLD: float = 0.70
    MIN_SIGNAL_SCORE: float = 0.20  # Bu altı kayıt edilmez

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b-instruct"
    OLLAMA_ENABLED: bool = True  # Otomatik detect edilir, false zorla kapatır
    OLLAMA_TIMEOUT_SECONDS: int = 120

    # UI
    ITEMS_PER_PAGE: int = 25
    DECK_TOP_SIGNALS: int = 10

    # Loglama
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def ensure_data_dir(cls, v: str) -> str:
        if v.startswith("sqlite:///"):
            db_path = Path(v.replace("sqlite:///", ""))
            db_path.parent.mkdir(parents=True, exist_ok=True)
        return v


settings = Settings()
