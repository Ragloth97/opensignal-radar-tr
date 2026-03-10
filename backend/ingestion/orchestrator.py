"""
Veri toplama orkestratörü.
Tüm kaynaklara uygun ingestor'ı yönlendirir.
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.db.models import Source, SourceType, SystemLog
from backend.ingestion.rss_ingestor import RSSIngestor
from backend.ingestion.web_scraper import WebScraper

logger = logging.getLogger(__name__)


class IngestionOrchestrator:
    """Tüm kaynak türleri için veri toplama koordinatörü."""

    def __init__(self, db: Session):
        self.db = db
        self.rss_ingestor = RSSIngestor(db)
        self.web_scraper = WebScraper(db)

    def run_all(self) -> dict:
        """Tüm aktif kaynakları tara."""
        active_sources = (
            self.db.query(Source)
            .filter(Source.is_active == True)
            .order_by(Source.priority_score.desc())
            .all()
        )

        results = {
            "total_sources": len(active_sources),
            "processed": 0,
            "skipped": 0,
            "new_articles": 0,
            "errors": 0,
        }

        for source in active_sources:
            if not self._should_check(source):
                results["skipped"] += 1
                continue

            try:
                new_count = self._ingest_source(source)
                results["new_articles"] += new_count
                results["processed"] += 1
            except Exception as e:
                logger.error(f"Kaynak hatası {source.name}: {e}")
                results["errors"] += 1

        self._log_run(results)
        return results

    def run_source(self, source_id: int) -> int:
        """Belirli bir kaynağı zorla çalıştır."""
        source = self.db.query(Source).get(source_id)
        if not source:
            raise ValueError(f"Kaynak bulunamadı: {source_id}")
        return self._ingest_source(source)

    def _ingest_source(self, source: Source) -> int:
        """Kaynak tipine göre doğru ingestor'ı kullan."""
        source_type = source.source_type

        rss_types = {SourceType.RSS}
        web_types = {
            SourceType.NEWS_SITE, SourceType.GOVERNMENT,
            SourceType.PRESS_ROOM, SourceType.CAREER_PAGE,
            SourceType.INCENTIVE, SourceType.TENDER,
        }

        if source_type in rss_types or source.feed_url:
            return self.rss_ingestor.ingest_source(source)
        elif source_type in web_types:
            return self.web_scraper.scrape_source_homepage(source)
        else:
            # Default: RSS dene, başarısız olursa web scrape
            count = self.rss_ingestor.ingest_source(source)
            if count == 0:
                count = self.web_scraper.scrape_source_homepage(source)
            return count

    def _should_check(self, source: Source) -> bool:
        """Kaynağın şu an kontrol edilmesi gerekiyor mu?"""
        if not source.last_checked_at:
            return True
        interval = timedelta(hours=source.check_interval_hours)
        return datetime.utcnow() - source.last_checked_at > interval

    def _log_run(self, results: dict):
        """Çalışma sonucunu sistem loguna kaydet."""
        log = SystemLog(
            event_type="ingestion_run",
            message=(
                f"Veri toplama tamamlandı: "
                f"{results['new_articles']} yeni makale, "
                f"{results['processed']} kaynak işlendi"
            ),
            details=results,
            level="INFO",
        )
        self.db.add(log)
        self.db.commit()
