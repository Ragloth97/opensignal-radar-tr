"""
Sinyal işleme orkestratörü.
Article'lardan Signal'lara dönüşüm pipeline'ı.
"""
import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.db.models import Article, Signal, ReviewStatus
from backend.signals.detector import RulesBasedDetector
from backend.signals.deduplicator import compute_duplicate_group_id
from backend.core.config import settings

logger = logging.getLogger(__name__)


class SignalProcessor:
    """
    İşlenmemiş makaleleri tarayıp sinyallere dönüştürür.
    AI katmanı varsa devreye alır, yoksa sadece rules kullanır.
    """

    def __init__(self, db: Session, ai_enabled: bool = True):
        self.db = db
        from backend.ai.enhancer import AIEnhancer
        self.enhancer = AIEnhancer()
        self.ai_enabled = self.enhancer.enabled

    def process_pending_articles(self, limit: int = 100) -> int:
        """
        İşlenmemiş makaleleri işle.
        Kaç tane sinyal üretildiğini döndür.
        """
        articles = (
            self.db.query(Article)
            .filter(Article.is_processed == False)
            .filter(Article.processing_attempts < 3)
            .order_by(Article.fetched_at.desc())
            .limit(limit)
            .all()
        )

        total_signals = 0
        for article in articles:
            try:
                count = self._process_article(article)
                total_signals += count
                article.is_processed = True
                article.processing_attempts += 1
            except Exception as e:
                logger.error(f"Article {article.id} işlenemedi: {e}")
                article.processing_attempts += 1

        self.db.commit()
        logger.info(
            f"{len(articles)} makale işlendi, "
            f"{total_signals} sinyal üretildi"
        )
        return total_signals

    def _process_article(self, article: Article) -> int:
        """Tek bir makaleyi işle ve sinyalleri kaydet."""
        source = article.source
        trust_score = source.trust_score if source else 0.5

        detector = RulesBasedDetector(source_trust_score=trust_score)
        signal_dicts = detector.analyze(article)

        if not signal_dicts:
            return 0

        saved = 0
        for sig_data in signal_dicts:
            if sig_data["composite_score"] < settings.MIN_SIGNAL_SCORE:
                continue

            # Duplicate group ID hesapla
            dup_group_id = compute_duplicate_group_id(
                signal_type=sig_data["signal_type"].value
                if hasattr(sig_data["signal_type"], 'value')
                else str(sig_data["signal_type"]),
                company=sig_data.get("detected_company"),
                country=sig_data.get("country"),
                industry=sig_data.get("industry"),
            )

            # Bu group'ta yakın zamanda kayıt var mı?
            is_duplicate = self._check_duplicate(dup_group_id, article.id)

            signal = Signal(
                article_id=article.id,
                detected_company=sig_data.get("detected_company"),
                industry=sig_data.get("industry"),
                country=sig_data.get("country"),
                city_or_region=sig_data.get("city_or_region"),
                signal_type=sig_data["signal_type"],
                signal_type_label_tr=sig_data.get("signal_type_label_tr"),
                summary_tr=sig_data.get("summary_tr"),
                confidence_score=sig_data["confidence_score"],
                impact_score=sig_data["impact_score"],
                relevance_score=sig_data.get("relevance_score", 0.0),
                composite_score=sig_data["composite_score"],
                evidence_phrases=sig_data.get("evidence_phrases", []),
                keywords_matched=sig_data.get("keywords_matched", []),
                relevant_sectors=sig_data.get("relevant_sectors", []),
                duplicate_group_id=dup_group_id,
                is_duplicate=is_duplicate,
                review_status=sig_data.get("review_status", ReviewStatus.PENDING),
                detection_method="rules",
                created_at=datetime.utcnow(),
            )

            self.db.add(signal)
            self.db.flush()  # ID ata

            # AI ile zenginleştir (Groq varsa)
            if self.ai_enabled:
                article_text = article.cleaned_text or article.raw_text or ""
                updates = self.enhancer.enhance_signal(
                    signal, article.title, article_text
                )
                for key, val in updates.items():
                    if hasattr(signal, key):
                        setattr(signal, key, val)

            saved += 1

        return saved

    def _check_duplicate(self, group_id: str, current_article_id: int) -> bool:
        """Aynı group ID'ye sahip yakın zamanlı sinyal var mı kontrol et."""
        from datetime import timedelta
        lookback = datetime.utcnow() - timedelta(days=7)

        existing = (
            self.db.query(Signal)
            .filter(Signal.duplicate_group_id == group_id)
            .filter(Signal.article_id != current_article_id)
            .filter(Signal.created_at >= lookback)
            .filter(Signal.is_duplicate == False)
            .first()
        )
        return existing is not None

    def reprocess_article(self, article_id: int) -> int:
        """Belirli bir makaleyi yeniden işle."""
        article = self.db.query(Article).get(article_id)
        if not article:
            return 0

        # Mevcut sinyalleri sil
        self.db.query(Signal).filter(Signal.article_id == article_id).delete()

        article.is_processed = False
        article.processing_attempts = 0
        self.db.commit()

        return self._process_article(article)
