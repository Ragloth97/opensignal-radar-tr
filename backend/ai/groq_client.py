"""
Groq API istemcisi — ücretsiz tier, LLaMA 3.3 70B, hızlı Türkçe destek.
GROQ_API_KEY env değişkeni gereklidir.
"""
import logging
from typing import Optional
import httpx
from backend.core.config import settings

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


class GroqClient:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.enabled = bool(self.api_key)
        if self.enabled:
            logger.info(f"Groq AI aktif: {GROQ_MODEL}")
        else:
            logger.info("Groq AI devre dışı (GROQ_API_KEY yok)")

    def is_available(self) -> bool:
        return self.enabled

    def generate(self, prompt: str, system: str = "", max_tokens: int = 300) -> Optional[str]:
        if not self.enabled:
            return None
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    GROQ_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": GROQ_MODEL,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": 0.3,
                    },
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"Groq API hatası: {e}")
            return None


groq = GroqClient()
