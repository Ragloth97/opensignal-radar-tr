"""
AI destekli sinyal zenginleştirme.
Önce Groq (ücretsiz, bulut), yoksa Ollama (lokal), yoksa kural tabanlı.
"""
import json
import re
import logging
from typing import Optional, Dict
from backend.db.models import Signal

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sen bir ekonomik istihbarat analistisin.
Verilen İngilizce haber başlığı ve metnini analiz edip Türkçe ekonomik içgörü üretirsin.
Her zaman kısa, kesin ve veri odaklı yanıt ver.
JSON formatında yanıt ver."""

SIGNAL_ENHANCE_PROMPT = """Aşağıdaki haberi analiz et:

BAŞLIK: {title}

METİN: {text}

Aşağıdaki JSON formatında yanıt ver (başka hiçbir şey yazma):
{{
  "company": "tespit edilen şirket adı veya null",
  "country": "ülke adı Türkçe veya null",
  "city": "şehir veya bölge veya null",
  "summary_tr": "2-3 cümlelik akıcı Türkçe özet. Şirket adı, ülke, yatırım miktarı ve projenin amacını içermeli. İngilizce kelime kullanma.",
  "signal_confirmed": true,
  "key_fact": "en önemli tek cümle Türkçe",
  "investment_amount": "yatırım miktarı varsa (örn: 1.8 milyar Euro) veya null"
}}"""


def _get_ai_client():
    """Mevcut AI istemcisini döndür: önce Groq, sonra Ollama."""
    try:
        from backend.ai.groq_client import groq
        if groq.is_available():
            return groq, "groq"
    except Exception:
        pass

    try:
        from backend.ai.ollama_client import ollama
        if ollama.is_available():
            return ollama, "ollama"
    except Exception:
        pass

    return None, None


class AIEnhancer:
    """AI ile sinyal kalitesini artırır. Groq → Ollama → kural tabanlı."""

    def __init__(self):
        self.client, self.provider = _get_ai_client()
        if self.client:
            logger.info(f"AI Enhancer aktif: {self.provider}")
        else:
            logger.info("AI Enhancer devre dışı — kural tabanlı özetler kullanılacak")

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def enhance_signal(
        self,
        signal: Signal,
        article_title: Optional[str],
        article_text: Optional[str],
    ) -> Dict:
        """Sinyali AI ile zenginleştir. Değişiklik dict'i döndür."""
        if not self.enabled:
            return {}

        if not article_text or len(article_text) < 100:
            return {}

        text_snippet = article_text[:2000]
        title = article_title or ""

        prompt = SIGNAL_ENHANCE_PROMPT.format(title=title, text=text_snippet)
        response = self.client.generate(prompt, system=SYSTEM_PROMPT, max_tokens=400)
        if not response:
            return {}

        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return {}

            data = json.loads(json_match.group(0))
            updates = {}

            if data.get("company") and not signal.detected_company:
                updates["detected_company"] = data["company"][:300]

            if data.get("country") and not signal.country:
                updates["country"] = data["country"][:100]

            if data.get("city") and not signal.city_or_region:
                updates["city_or_region"] = data["city"][:200]

            if data.get("summary_tr"):
                updates["summary_tr"] = data["summary_tr"][:600]

            if data.get("key_fact"):
                existing = signal.evidence_phrases or []
                if data["key_fact"] not in existing:
                    updates["evidence_phrases"] = [data["key_fact"]] + existing

            if data.get("signal_confirmed") is False:
                updates["confidence_score"] = max(0.0, signal.confidence_score - 0.15)

            updates["detection_method"] = f"ai_enhanced_{self.provider}"
            updates["ai_model_used"] = self.provider

            return updates

        except Exception as e:
            logger.debug(f"AI enhance parse hatası: {e}")
            return {}

    def generate_turkish_summary(self, title: str, text: str) -> Optional[str]:
        """Kısa Türkçe özet üret."""
        if not self.enabled:
            return None

        prompt = (
            "Bu haberi 2-3 cümleyle Türkçe özetle. "
            "Şirket adı, ülke, miktar ve projenin amacını belirt. "
            "Sadece özeti yaz, başka hiçbir şey ekleme. İngilizce kelime kullanma.\n\n"
            f"BAŞLIK: {title}\n\nMETİN: {text[:1000]}"
        )
        return self.client.generate(prompt, max_tokens=200)
