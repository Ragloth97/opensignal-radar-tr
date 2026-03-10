"""
Web scraping modülü.
trafilatura ile içerik çıkarma, BeautifulSoup ile yapısal parse.
"""
import logging
import re
from datetime import datetime
from typing import Optional, Tuple
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from backend.db.models import Source, Article
from backend.ingestion.fetcher import fetch_url_sync
from backend.signals.deduplicator import normalize_url, compute_text_hash
from backend.core.config import settings

logger = logging.getLogger(__name__)


def extract_article_content(html: str, url: str) -> Tuple[str, Optional[str]]:
    """
    HTML'den makale içeriğini ve yayın tarihini çıkar.
    (cleaned_text, published_date_str) döndür.
    """
    # Önce trafilatura dene - en iyi sonucu verir
    try:
        import trafilatura
        result = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            with_metadata=True,
            output_format='json',
        )
        if result:
            import json
            data = json.loads(result)
            text = data.get("text", "")
            date = data.get("date", "")
            if text and len(text) > 200:
                return text[:8000], date
    except Exception as e:
        logger.debug(f"Trafilatura hatası: {e}")

    # Fallback: BeautifulSoup
    try:
        soup = BeautifulSoup(html, "lxml")

        # Gereksiz elementleri kaldır
        for tag in soup.find_all(['script', 'style', 'nav', 'header',
                                   'footer', 'aside', 'iframe', 'form']):
            tag.decompose()

        # Ana içerik alanını bul
        content_selectors = [
            'article', '[role="main"]', '.article-body', '.article-content',
            '.post-content', '.entry-content', '.news-content', 'main',
        ]

        content_el = None
        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                break

        if not content_el:
            content_el = soup.find('body')

        if content_el:
            text = content_el.get_text(separator=' ', strip=True)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:8000], None

    except Exception as e:
        logger.debug(f"BeautifulSoup hatası: {e}")

    return "", None


def extract_title(html: str) -> Optional[str]:
    """HTML'den başlık çıkar."""
    try:
        soup = BeautifulSoup(html, "lxml")

        # OG title tercih et
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()[:500]

        # h1
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)[:500]

        # title tag
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True)[:500]

    except Exception:
        pass
    return None


def extract_published_date(html: str) -> Optional[datetime]:
    """HTML'den yayın tarihini çıkar."""
    try:
        soup = BeautifulSoup(html, "lxml")
        from dateutil import parser as dateparser

        # Meta tags
        for attr_name in ["article:published_time", "og:article:published_time",
                           "datePublished", "date"]:
            meta = soup.find("meta", property=attr_name) or soup.find("meta", attrs={"name": attr_name})
            if meta and meta.get("content"):
                try:
                    return dateparser.parse(meta["content"])
                except Exception:
                    pass

        # time element
        time_el = soup.find("time", attrs={"datetime": True})
        if time_el:
            try:
                return dateparser.parse(time_el["datetime"])
            except Exception:
                pass

    except Exception:
        pass
    return None


class WebScraper:
    """RSS dışı web sitelerini taran sınıf."""

    def __init__(self, db: Session):
        self.db = db

    def scrape_source_homepage(self, source: Source) -> int:
        """
        Kaynak ana sayfasını veya listeleme sayfasını tara.
        Bulunan bağlantıları takip et ve makale olarak kaydet.
        """
        logger.info(f"Web scraping: {source.name} ({source.base_url})")

        html, status = fetch_url_sync(source.base_url)
        if not html:
            logger.warning(f"Sayfa çekilemedi: {source.base_url} (HTTP {status})")
            return 0

        # Sayfadaki makale linklerini bul
        article_links = self._find_article_links(html, source.base_url)

        new_count = 0
        for link in article_links[:settings.MAX_ARTICLES_PER_SOURCE]:
            try:
                added = self._scrape_article(link, source)
                if added:
                    new_count += 1
            except Exception as e:
                logger.error(f"Makale scrape hatası {link}: {e}")

        self.db.commit()
        source.last_checked_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"{source.name}: {new_count} yeni makale scrape edildi")
        return new_count

    def _find_article_links(self, html: str, base_url: str) -> list:
        """Sayfadan makale linklerini topla."""
        from urllib.parse import urljoin, urlparse
        soup = BeautifulSoup(html, "lxml")
        base_domain = urlparse(base_url).netloc

        links = []
        seen = set()

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(base_url, href)
            normalized = normalize_url(full_url)

            if normalized in seen:
                continue
            seen.add(normalized)

            parsed = urlparse(normalized)

            # Aynı domain kontrolü
            if parsed.netloc != base_domain:
                continue

            # URL path uzunluğu - kısa URL'ler genellikle kategorilerdir
            path = parsed.path
            if len(path) < 10:
                continue

            # Yaygın makale URL pattern'leri
            if any(x in path for x in [
                '/news/', '/article/', '/story/', '/press/', '/release/',
                '/haber/', '/icerik/', '/post/', '/blog/', '/2024/', '/2025/',
                '/2026/', '-html', '.html', '/p/'
            ]):
                links.append(normalized)

        return links[:100]

    def _scrape_article(self, url: str, source: Source) -> bool:
        """Tek bir makaleyi scrape et ve kaydet."""
        # Duplicate kontrolü
        existing = self.db.query(Article).filter(Article.url == url).first()
        if existing:
            return False

        html, status = fetch_url_sync(url)
        if not html:
            return False

        # İçerik çıkar
        cleaned_text, date_str = extract_article_content(html, url)
        if not cleaned_text or len(cleaned_text) < 150:
            return False

        # Başlık ve tarih
        title = extract_title(html)
        published_at = extract_published_date(html)

        if not published_at and date_str:
            try:
                from dateutil import parser as dateparser
                published_at = dateparser.parse(date_str)
            except Exception:
                pass

        text_hash = compute_text_hash(cleaned_text)

        # Hash duplicate kontrolü
        hash_exists = (
            self.db.query(Article)
            .filter(Article.raw_text_hash == text_hash)
            .first()
        )
        if hash_exists:
            return False

        article = Article(
            source_id=source.id,
            title=title,
            url=url,
            published_at=published_at or datetime.utcnow(),
            cleaned_text=cleaned_text[:8000],
            raw_text_hash=text_hash,
            language=source.language or "en",
            fetched_at=datetime.utcnow(),
            is_processed=False,
        )

        self.db.add(article)
        return True
