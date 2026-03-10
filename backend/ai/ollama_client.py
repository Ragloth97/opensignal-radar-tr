"""
Ollama AI istemcisi.
Ollama çalışmıyorsa sessizce devre dışı kalır.
"""
import logging
from typing import Optional, Dict, Any
import httpx
from backend.core.config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """Ollama API istemcisi."""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT_SECONDS
        self._available: Optional[bool] = None

    def is_available(self) -> bool:
        """Ollama'nın çalışıp çalışmadığını kontrol et."""
        if not settings.OLLAMA_ENABLED:
            return False

        if self._available is not None:
            return self._available

        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self.base_url}/api/tags")
                self._available = response.status_code == 200

                if self._available:
                    # Model listesini kontrol et
                    data = response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    model_available = any(
                        self.model.split(":")[0] in m for m in models
                    )
                    if not model_available:
                        logger.warning(
                            f"Ollama çalışıyor ama {self.model} modeli bulunamadı. "
                            f"Mevcut modeller: {models}"
                        )
                        self._available = False

                return self._available

        except Exception as e:
            logger.debug(f"Ollama erişilemiyor: {e}")
            self._available = False
            return False

    def generate(self, prompt: str, system: str = "") -> Optional[str]:
        """Ollama'ya prompt gönder ve yanıt al."""
        if not self.is_available():
            return None

        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_predict": 512,
                },
            }

            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "").strip()
                else:
                    logger.error(f"Ollama HTTP {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Ollama generate hatası: {e}")
            self._available = False
            return None

    def reset_cache(self):
        """Availability cache'ini sıfırla."""
        self._available = None


# Singleton instance
ollama = OllamaClient()
