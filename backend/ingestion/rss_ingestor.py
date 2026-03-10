"""
RSS / Atom feed okuyucu.
feedparser kullanır, her feed entry'sini Article'a dönüştürür.
"""
import logging
from datetime import datetime
from typing import List, Optional
import feedparser
from dateutil import parser as dateparser
from sqlalchemy.orm import Session

from backend.db.models import Source, Article
from backend.signals.deduplicator import compute_url_hash, normalize_url
from backend.core.config import settings

logger = logging.getLogger(__name__)


class RSSIngestor:
    """RSS/Atom feed'lerden makale çeken sınıf."""

    def __init__(self, db: Session):
        self.db = db

    def ingest_source(self, source: Source) -> int:
        """
        Kaynağı tara ve yeni makaleleri kaydet.
        Kaç yeni makale eklendiğini döndür.
        """
        feed_url = source.feed_url or source.base_url
        logger.info(f"RSS tarıyor: {source.name} ({feed_url})")

        try:
            feed = feedparser.parse(
                feed_url,
                agent=settings.USER_AGENT,
                request_headers={"Accept": "application/rss+xml, application/atom+xml"},
            )

            if not feed.entries:
                logger.warning(f"Feed boş veya parse edilemedi: {feed_url}")
                return 0

            new_count = 0
            for entry in feed.entries[:settings.MAX_ARTICLES_PER_SOURCE]:
                try:
                    added = self._process_entry(entry, source)
                    if added:
                        new_count += 1
                except Exception as e:
                    logger.error(f"Entry işlenemedi: {e}")

            self.db.commit()

            # Son kontrol zamanını güncelle
            source.last_checked_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"{source.name}: {new_count} yeni makale eklendi")
            return new_count

        except Exception as e:
            logger.error(f"RSS ingest hatası {source.name}: {e}")
            return 0

    def _process_entry(self, entry: dict, source: Source) -> bool:
        """
        Tek bir feed entry'sini işle.
        True döndür eğer yeni makale eklediyse.
        """
        url = entry.get("link") or entry.get("url", "")
        if not url:
            return False

        url = normalize_url(url)

        # Duplicate kontrolü
        existing = self.db.query(Article).filter(Article.url == url).first()
        if existing:
            return False

        # Tarih parse
        published_at = self._parse_date(entry)

        # İçerik
        title = entry.get("title", "").strip()
        summary = entry.get("summary", "") or entry.get("description", "")
        content = ""
        if hasattr(entry, "content") and entry.content:
            content = entry.content[0].get("value", "")

        raw_text = content or summary or title

        # Hash
        from backend.signals.deduplicator import compute_text_hash
        text_hash = compute_text_hash(raw_text) if raw_text else None

        article = Article(
            source_id=source.id,
            title=title[:500] if title else None,
            url=url,
            published_at=published_at,
            raw_text=raw_text[:10000] if raw_text else None,
            cleaned_text=self._clean_text(raw_text)[:5000] if raw_text else None,
            raw_text_hash=text_hash,
            language=source.language or "en",
            fetched_at=datetime.utcnow(),
            is_processed=False,
        )

        self.db.add(article)
        return True

    def _parse_date(self, entry: dict) -> Optional[datetime]:
        """Feed entry'sinden tarih parse et."""
        for field in ["published_parsed", "updated_parsed", "created_parsed"]:
            parsed = entry.get(field)
            if parsed:
                try:
                    import time
                    return datetime.fromtimestamp(time.mktime(parsed))
                except Exception:
                    pass

        for field in ["published", "updated", "created"]:
            date_str = entry.get(field, "")
            if date_str:
                try:
                    return dateparser.parse(date_str)
                except Exception:
                    pass

        return datetime.utcnow()

    def _clean_text(self, text: str) -> str:
        """HTML tag'larını ve gereksiz boşlukları temizle."""
        if not text:
            return ""
        from bs4 import BeautifulSoup
        import re
        soup = BeautifulSoup(text, "html.parser")
        clean = soup.get_text(separator=" ")
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean
