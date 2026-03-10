"""
Intelligence Deck API endpoint'leri.
Stratejik briefing formatında veri üretir.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from backend.db.database import get_db
from backend.db.models import Signal, TrendCluster, Source, Article, ReviewStatus
from backend.signals.keywords import SIGNAL_TYPE_LABELS_TR, INDUSTRY_LABELS_TR
from backend.core.config import settings

router = APIRouter(prefix="/api/deck", tags=["deck"])


@router.get("/briefing")
def get_daily_briefing(db: Session = Depends(get_db)):
    """
    Günlük istihbarat briefing verisi.
    Deck görünümü için tüm section'ları içerir.
    """
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    week_start = datetime.utcnow() - timedelta(days=7)

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "section_1_overview": _get_overview(db, today_start, week_start),
        "section_2_critical": _get_critical_signals(db, week_start),
        "section_3_patterns": _get_patterns(db),
        "section_4_regional": _get_regional_view(db, week_start),
        "section_5_sectoral": _get_sectoral_view(db, week_start),
        "section_6_watchlist": _get_watchlist(db, week_start),
        "section_7_raw": _get_raw_findings(db, today_start),
    }


def _get_overview(db: Session, today_start: datetime, week_start: datetime) -> dict:
    """Bölüm 1: Genel Bakış."""
    today_count = (
        db.query(func.count(Signal.id))
        .filter(Signal.created_at >= today_start)
        .filter(Signal.is_duplicate == False)
        .scalar()
    )

    week_count = (
        db.query(func.count(Signal.id))
        .filter(Signal.created_at >= week_start)
        .filter(Signal.is_duplicate == False)
        .scalar()
    )

    high_impact_today = (
        db.query(func.count(Signal.id))
        .filter(Signal.created_at >= today_start)
        .filter(Signal.impact_score >= settings.HIGH_IMPACT_THRESHOLD)
        .filter(Signal.is_duplicate == False)
        .scalar()
    )

    # Öne çıkan ülkeler (bu hafta)
    top_countries = (
        db.query(Signal.country, func.count(Signal.id).label("cnt"))
        .filter(Signal.created_at >= week_start)
        .filter(Signal.country.isnot(None))
        .filter(Signal.is_duplicate == False)
        .group_by(Signal.country)
        .order_by(desc("cnt"))
        .limit(3)
        .all()
    )

    # Öne çıkan sektörler (bu hafta)
    top_sectors = (
        db.query(Signal.industry, func.count(Signal.id).label("cnt"))
        .filter(Signal.created_at >= week_start)
        .filter(Signal.industry.isnot(None))
        .filter(Signal.is_duplicate == False)
        .group_by(Signal.industry)
        .order_by(desc("cnt"))
        .limit(3)
        .all()
    )

    # Ana tema - en çok hangi sinyal tipi var
    top_type = (
        db.query(Signal.signal_type, func.count(Signal.id).label("cnt"))
        .filter(Signal.created_at >= week_start)
        .filter(Signal.is_duplicate == False)
        .group_by(Signal.signal_type)
        .order_by(desc("cnt"))
        .first()
    )

    main_theme = None
    if top_type:
        label = SIGNAL_TYPE_LABELS_TR.get(top_type.signal_type, "")
        main_theme = f"Bu hafta öne çıkan ana tema: {label} ({top_type.cnt} sinyal)"

    return {
        "today_signal_count": today_count,
        "week_signal_count": week_count,
        "high_impact_today": high_impact_today,
        "top_countries": [
            {"country": r.country, "count": r.cnt} for r in top_countries
        ],
        "top_sectors": [
            {
                "sector": r.industry,
                "sector_label": INDUSTRY_LABELS_TR.get(r.industry, r.industry),
                "count": r.cnt,
            }
            for r in top_sectors
        ],
        "main_theme": main_theme,
    }


def _get_critical_signals(db: Session, week_start: datetime) -> list:
    """Bölüm 2: Kritik Gelişmeler."""
    signals = (
        db.query(Signal)
        .filter(Signal.created_at >= week_start)
        .filter(Signal.is_duplicate == False)
        .filter(Signal.review_status != ReviewStatus.REJECTED)
        .order_by(desc(Signal.composite_score))
        .limit(settings.DECK_TOP_SIGNALS)
        .all()
    )

    result = []
    for sig in signals:
        article = db.query(Article).get(sig.article_id) if sig.article_id else None
        result.append({
            "id": sig.id,
            "signal_type": sig.signal_type.value if hasattr(sig.signal_type, 'value') else sig.signal_type,
            "signal_type_label_tr": sig.signal_type_label_tr or SIGNAL_TYPE_LABELS_TR.get(sig.signal_type, ""),
            "detected_company": sig.detected_company,
            "country": sig.country,
            "industry": sig.industry,
            "industry_label": INDUSTRY_LABELS_TR.get(sig.industry, sig.industry) if sig.industry else None,
            "summary_tr": sig.summary_tr,
            "confidence_score": sig.confidence_score,
            "impact_score": sig.impact_score,
            "composite_score": sig.composite_score,
            "evidence_phrases": (sig.evidence_phrases or [])[:2],
            "relevant_sectors": sig.relevant_sectors or [],
            "article_title": article.title if article else None,
            "article_url": article.url if article else None,
            "article_published_at": article.published_at.isoformat() if article and article.published_at else None,
            "created_at": sig.created_at.isoformat() if sig.created_at else None,
            "why_important": _generate_importance_text(sig),
        })

    return result


def _get_patterns(db: Session) -> list:
    """Bölüm 3: Gelişen Örüntüler."""
    clusters = (
        db.query(TrendCluster)
        .filter(TrendCluster.is_active == True)
        .filter(TrendCluster.signal_count >= 3)
        .order_by(desc(TrendCluster.cluster_score))
        .limit(6)
        .all()
    )

    return [
        {
            "id": c.id,
            "label": c.label,
            "description_tr": c.description_tr,
            "sector": c.sector,
            "sector_label": INDUSTRY_LABELS_TR.get(c.sector, c.sector) if c.sector else None,
            "geography": c.geography,
            "signal_count": c.signal_count,
            "cluster_score": c.cluster_score,
            "last_seen_at": c.last_seen_at.isoformat() if c.last_seen_at else None,
        }
        for c in clusters
    ]


def _get_regional_view(db: Session, week_start: datetime) -> list:
    """Bölüm 4: Bölgesel Görünüm."""
    country_data = (
        db.query(
            Signal.country,
            func.count(Signal.id).label("signal_count"),
            func.avg(Signal.composite_score).label("avg_score"),
            func.max(Signal.impact_score).label("max_impact"),
        )
        .filter(Signal.created_at >= week_start)
        .filter(Signal.country.isnot(None))
        .filter(Signal.is_duplicate == False)
        .group_by(Signal.country)
        .order_by(desc("signal_count"))
        .limit(10)
        .all()
    )

    result = []
    for row in country_data:
        # Bu ülkedeki dominant sektör
        top_sector = (
            db.query(Signal.industry, func.count(Signal.id).label("cnt"))
            .filter(Signal.created_at >= week_start)
            .filter(Signal.country == row.country)
            .filter(Signal.industry.isnot(None))
            .group_by(Signal.industry)
            .order_by(desc("cnt"))
            .first()
        )

        result.append({
            "country": row.country,
            "signal_count": row.signal_count,
            "avg_composite_score": round(row.avg_score or 0, 3),
            "max_impact_score": round(row.max_impact or 0, 3),
            "dominant_sector": top_sector.industry if top_sector else None,
            "dominant_sector_label": INDUSTRY_LABELS_TR.get(
                top_sector.industry, top_sector.industry
            ) if top_sector else None,
        })

    return result


def _get_sectoral_view(db: Session, week_start: datetime) -> list:
    """Bölüm 5: Sektörel Görünüm."""
    sector_data = (
        db.query(
            Signal.industry,
            func.count(Signal.id).label("signal_count"),
            func.avg(Signal.confidence_score).label("avg_confidence"),
            func.avg(Signal.impact_score).label("avg_impact"),
        )
        .filter(Signal.created_at >= week_start)
        .filter(Signal.industry.isnot(None))
        .filter(Signal.is_duplicate == False)
        .group_by(Signal.industry)
        .order_by(desc("signal_count"))
        .all()
    )

    result = []
    for row in sector_data:
        # Bu sektördeki top sinyal tipi
        top_type = (
            db.query(Signal.signal_type, func.count(Signal.id).label("cnt"))
            .filter(Signal.created_at >= week_start)
            .filter(Signal.industry == row.industry)
            .group_by(Signal.signal_type)
            .order_by(desc("cnt"))
            .first()
        )

        # Bu sektördeki aktif ülkeler
        active_countries = (
            db.query(Signal.country)
            .filter(Signal.created_at >= week_start)
            .filter(Signal.industry == row.industry)
            .filter(Signal.country.isnot(None))
            .distinct()
            .limit(3)
            .all()
        )

        result.append({
            "sector": row.industry,
            "sector_label": INDUSTRY_LABELS_TR.get(row.industry, row.industry),
            "signal_count": row.signal_count,
            "avg_confidence": round(row.avg_confidence or 0, 3),
            "avg_impact": round(row.avg_impact or 0, 3),
            "top_signal_type": (
                top_type.signal_type.value
                if top_type and hasattr(top_type.signal_type, 'value')
                else (top_type.signal_type if top_type else None)
            ),
            "top_signal_type_label": (
                SIGNAL_TYPE_LABELS_TR.get(top_type.signal_type)
                if top_type else None
            ),
            "active_countries": [r.country for r in active_countries],
        })

    return result


def _get_watchlist(db: Session, week_start: datetime) -> list:
    """Bölüm 6: Yakından İzlenmesi Gerekenler."""
    # Orta skor ama stratejik
    signals = (
        db.query(Signal)
        .filter(Signal.created_at >= week_start)
        .filter(Signal.is_duplicate == False)
        .filter(Signal.review_status == ReviewStatus.NEEDS_REVIEW)
        .order_by(desc(Signal.impact_score))
        .limit(8)
        .all()
    )

    # Ayrıca yeni ülkelerden gelen sinyaller
    if len(signals) < 8:
        strategic_types = ["semiconductor", "data_center", "energy_project", "new_facility"]
        additional = (
            db.query(Signal)
            .filter(Signal.created_at >= week_start)
            .filter(Signal.is_duplicate == False)
            .filter(Signal.confidence_score.between(0.40, 0.65))
            .filter(Signal.impact_score >= 0.55)
            .order_by(desc(Signal.impact_score))
            .limit(8 - len(signals))
            .all()
        )
        signals.extend(additional)

    return [
        {
            "id": s.id,
            "signal_type": s.signal_type.value if hasattr(s.signal_type, 'value') else s.signal_type,
            "signal_type_label_tr": s.signal_type_label_tr or SIGNAL_TYPE_LABELS_TR.get(s.signal_type, ""),
            "detected_company": s.detected_company,
            "country": s.country,
            "industry": s.industry,
            "summary_tr": s.summary_tr,
            "confidence_score": s.confidence_score,
            "impact_score": s.impact_score,
            "watch_reason": _get_watch_reason(s),
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in signals
    ]


def _get_raw_findings(db: Session, today_start: datetime) -> list:
    """Bölüm 7: Ham Bulgular."""
    from datetime import timedelta
    two_days_ago = datetime.utcnow() - timedelta(days=2)

    articles = (
        db.query(Article)
        .filter(Article.fetched_at >= two_days_ago)
        .filter(Article.is_processed == True)
        .order_by(desc(Article.fetched_at))
        .limit(20)
        .all()
    )

    result = []
    for article in articles:
        source = db.query(Source).get(article.source_id) if article.source_id else None
        signal_count = db.query(func.count(Signal.id)).filter(
            Signal.article_id == article.id
        ).scalar()

        result.append({
            "article_id": article.id,
            "title": article.title,
            "url": article.url,
            "source_name": source.name if source else None,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "fetched_at": article.fetched_at.isoformat() if article.fetched_at else None,
            "signal_count": signal_count,
        })

    return result


def _generate_importance_text(signal: Signal) -> str:
    """Sinyalin neden önemli olduğunu açıkla."""
    from backend.signals.keywords import SIGNAL_TYPE_LABELS_TR, INDUSTRY_LABELS_TR
    parts = []

    type_label = SIGNAL_TYPE_LABELS_TR.get(signal.signal_type, "")

    if signal.impact_score >= 0.80:
        parts.append("Yüksek etkili gelişme")
    elif signal.impact_score >= 0.60:
        parts.append("Orta-yüksek etki potansiyeli")

    if signal.industry:
        label = INDUSTRY_LABELS_TR.get(signal.industry, signal.industry)
        parts.append(f"{label} sektörünü doğrudan etkiliyor")

    if signal.relevant_sectors and len(signal.relevant_sectors) > 1:
        other_sectors = [
            INDUSTRY_LABELS_TR.get(s, s)
            for s in signal.relevant_sectors[:2]
        ]
        parts.append(f"Yan etkiler: {', '.join(other_sectors)}")

    return ". ".join(parts) if parts else "Stratejik öneme sahip gelişme."


def _get_watch_reason(signal: Signal) -> str:
    """İzleme listesine alınma gerekçesi."""
    if signal.review_status == ReviewStatus.NEEDS_REVIEW:
        return "Doğrulama bekliyor — ikincil kaynaklarla teyit önerilir"
    if signal.confidence_score < 0.55:
        return "Sinyal gücü orta — gelişme takip edilmeli"
    if signal.impact_score >= 0.60:
        return "Yüksek potansiyel etki — yakından izlenmeli"
    return "Stratejik öneme sahip erken sinyal"
