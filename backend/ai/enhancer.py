"""
AI destekli sinyal zenginleştirme.
Ollama varsa rules-based sinyalleri geliştirir.
"""
import json
import logging
from typing import Optional, Dict
from backend.ai.ollama_client import ollama
from backend.db.models import Signal

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sen bir ekonomik istihbarat analistisin.
Verilen haber başlığı ve metnini analiz ederek Türkçe ekonomik içgörü üretirsin.
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
  "summary_tr": "50-100 kelimelik Türkçe özet",
  "signal_confirmed": true/false,
  "key_fact": "en önemli tek cümle",
  "investment_amount": "yatırım miktarı varsa veya null"
}}"""


class AIEnhancer:
    """Ollama ile sinyal kalitesini artırır."""

    def __init__(self):
        self.enabled = ollama.is_available()
        if self.enabled:
            logger.info(f"AI Enhancer aktif: {ollama.model}")
        else:
            logger.info("AI Enhancer devre dışı (Ollama bulunamadı)")

    def enhance_signal(
        self,
        signal: Signal,
        article_title: Optional[str],
        article_text: Optional[str],
    ) -> Dict:
        """
        Sinyali AI ile zenginleştir.
        Değişiklik dict'i döndür (Signal'e uygulanmak üzere).
        """
        if not self.enabled:
            return {}

        if not article_text or len(article_text) < 100:
            return {}

        # Token limiti için metni kırp
        text_snippet = article_text[:1500]
        title = article_title or ""

        prompt = SIGNAL_ENHANCE_PROMPT.format(
            title=title,
            text=text_snippet,
        )

        response = ollama.generate(prompt, system=SYSTEM_PROMPT)
        if not response:
            return {}

        try:
            # JSON çıktısını parse et
            # Bazen model etrafına metin ekler, sadece JSON'u çıkar
            import re
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
                updates["summary_tr"] = data["summary_tr"][:500]

            if data.get("key_fact"):
                # Kanıt cümlelerine ekle
                existing = signal.evidence_phrases or []
                if data["key_fact"] not in existing:
                    updates["evidence_phrases"] = [data["key_fact"]] + existing

            if data.get("signal_confirmed") is False:
                # AI sinyali doğrulamadı, skoru düşür
                updates["confidence_score"] = max(0.0, signal.confidence_score - 0.15)

            updates["detection_method"] = "ai_enhanced"
            updates["ai_model_used"] = ollama.model

            return updates

        except Exception as e:
            logger.debug(f"AI enhance parse hatası: {e}")
            return {}

    def generate_turkish_summary(
        self, title: str, text: str
    ) -> Optional[str]:
        """Kısa Türkçe özet üret."""
        if not self.enabled:
            return None

        prompt = (
            f"Bu haberi 2-3 cümleyle Türkçe özetle. "
            f"Sadece özeti yaz, başka hiçbir şey ekleme.\n\n"
            f"BAŞLIK: {title}\n\nMETİN: {text[:800]}"
        )

        return ollama.generate(prompt)
