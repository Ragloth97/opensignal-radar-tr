"""
Sinyal ve makale tekilleştirme modülü.
URL hash ve içerik benzerliği üzerinden çalışır.
"""
import hashlib
import re
from typing import Optional
from urllib.parse import urlparse, urlunparse


def normalize_url(url: str) -> str:
    """URL'yi normalize et - tracking parametrelerini temizle."""
    try:
        parsed = urlparse(url)
        # Tracking parametrelerini kaldır
        tracking_params = {
            'utm_source', 'utm_medium', 'utm_campaign',
            'utm_term', 'utm_content', 'fbclid', 'gclid',
            'ref', 'source', 'campaign',
        }
        if parsed.query:
            params = [
                p for p in parsed.query.split('&')
                if p.split('=')[0].lower() not in tracking_params
            ]
            cleaned_query = '&'.join(params)
        else:
            cleaned_query = ''

        cleaned = urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),
            parsed.path.rstrip('/'),
            parsed.params,
            cleaned_query,
            '',  # Fragment kaldır
        ))
        return cleaned
    except Exception:
        return url


def compute_text_hash(text: str) -> str:
    """Metin için SHA-256 hash üret."""
    normalized = re.sub(r'\s+', ' ', text.strip().lower())
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def compute_url_hash(url: str) -> str:
    """URL için normalized hash üret."""
    normalized = normalize_url(url)
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()


def compute_duplicate_group_id(
    signal_type: str,
    company: Optional[str],
    country: Optional[str],
    industry: Optional[str],
) -> str:
    """
    Aynı olayı temsil eden sinyalleri gruplamak için group ID üret.
    Şirket + sinyal tipi + ülke kombinasyonu.
    """
    parts = [
        signal_type or "",
        (company or "").lower()[:50],
        (country or "").lower(),
        (industry or "").lower(),
    ]
    combined = "|".join(parts)
    return hashlib.md5(combined.encode('utf-8')).hexdigest()[:16]


def extract_domain(url: str) -> str:
    """URL'den domain adını çıkar."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return ""
