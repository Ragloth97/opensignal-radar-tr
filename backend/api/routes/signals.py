"""
Sinyal API endpoint'leri.
"""
from typing import Optional, List
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from pydantic import BaseModel

from backend.db.database import get_db
from backend.db.models import Signal, Article, Source, ReviewStatus, SignalType

router = APIRouter(prefix="/api/signals", tags=["signals"])


class SignalReviewRequest(BaseModel):
    status: str
    note: Optional[str] = None


class SignalResponse(BaseModel):
    id: int
    article_id: int
    detected_company: Optional[str]
    industry: Optional[str]
    country: Optional[str]
    city_or_region: Optional[str]
    signal_type: str
    signal_type_label_tr: Optional[str]
    summary_tr: Optional[str]
    confidence_score: float
    impact_score: float
    composite_score: float
    evidence_phrases: Optional[list]
    relevant_sectors: Optional[list]
    review_status: str
    is_duplicate: bool
    detection_method: str
    created_at: datetime
    article_title: Optional[str] = None
    article_url: Optional[str] = None
    source_name: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/", response_model=dict)
def list_signals(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    signal_type: Optional[str] = None,
    industry: Optional[str] = None,
    country: Optional[str] = None,
    review_status: Optional[str] = None,
    min_confidence: Optional[float] = Query(None, ge=0, le=1),
    min_impact: Optional[float] = Query(None, ge=0, le=1),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    include_duplicates: bool = False,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Filtrelenmiş sinyal listesi."""
    query = db.query(Signal)

    if not include_duplicates:
        query = query.filter(Signal.is_duplicate == False)

    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)
    if industry:
        query = query.filter(Signal.industry == industry)
    if country:
        query = query.filter(Signal.country.ilike(f"%{country}%"))
    if review_status:
        query = query.filter(Signal.review_status == review_status)
    if min_confidence is not None:
        query = query.filter(Signal.confidence_score >= min_confidence)
    if min_impact is not None:
        query = query.filter(Signal.impact_score >= min_impact)
    if date_from:
        query = query.filter(Signal.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(Signal.created_at <= datetime.combine(date_to, datetime.max.time()))
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Signal.detected_company.ilike(search_term),
                Signal.summary_tr.ilike(search_term),
                Signal.country.ilike(search_term),
            )
        )

    total = query.count()
    signals = (
        query
        .order_by(desc(Signal.composite_score), desc(Signal.created_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    items = []
    for sig in signals:
        item = _signal_to_dict(sig, db)
        items.append(item)

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@router.get("/{signal_id}", response_model=dict)
def get_signal(signal_id: int, db: Session = Depends(get_db)):
    """Tek bir sinyal detayı."""
    signal = db.query(Signal).get(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Sinyal bulunamadı")
    return _signal_to_dict(signal, db)


@router.patch("/{signal_id}/review")
def review_signal(
    signal_id: int,
    request: SignalReviewRequest,
    db: Session = Depends(get_db),
):
    """Sinyal inceleme durumunu güncelle."""
    signal = db.query(Signal).get(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Sinyal bulunamadı")

    valid_statuses = [s.value for s in ReviewStatus]
    if request.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Geçersiz durum")

    signal.review_status = request.status
    signal.review_note = request.note
    signal.reviewed_at = datetime.utcnow()
    db.commit()

    return {"success": True, "signal_id": signal_id, "new_status": request.status}


@router.get("/stats/summary", response_model=dict)
def get_signal_stats(db: Session = Depends(get_db)):
    """Sinyal istatistikleri özeti."""
    from sqlalchemy import func
    from datetime import timedelta

    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    week_start = datetime.utcnow() - timedelta(days=7)

    total = db.query(func.count(Signal.id)).scalar()
    today_count = (
        db.query(func.count(Signal.id))
        .filter(Signal.created_at >= today_start)
        .scalar()
    )
    high_impact = (
        db.query(func.count(Signal.id))
        .filter(Signal.impact_score >= 0.70)
        .filter(Signal.is_duplicate == False)
        .scalar()
    )
    needs_review = (
        db.query(func.count(Signal.id))
        .filter(Signal.review_status == ReviewStatus.NEEDS_REVIEW)
        .scalar()
    )
    week_count = (
        db.query(func.count(Signal.id))
        .filter(Signal.created_at >= week_start)
        .filter(Signal.is_duplicate == False)
        .scalar()
    )

    # Ülke dağılımı
    country_dist = (
        db.query(Signal.country, func.count(Signal.id).label("count"))
        .filter(Signal.country.isnot(None))
        .filter(Signal.created_at >= week_start)
        .group_by(Signal.country)
        .order_by(desc("count"))
        .limit(5)
        .all()
    )

    # Sektör dağılımı
    sector_dist = (
        db.query(Signal.industry, func.count(Signal.id).label("count"))
        .filter(Signal.industry.isnot(None))
        .filter(Signal.created_at >= week_start)
        .group_by(Signal.industry)
        .order_by(desc("count"))
        .limit(5)
        .all()
    )

    # Sinyal tipi dağılımı
    type_dist = (
        db.query(Signal.signal_type, func.count(Signal.id).label("count"))
        .filter(Signal.created_at >= week_start)
        .filter(Signal.is_duplicate == False)
        .group_by(Signal.signal_type)
        .order_by(desc("count"))
        .limit(8)
        .all()
    )

    return {
        "total_signals": total,
        "today_signals": today_count,
        "week_signals": week_count,
        "high_impact_signals": high_impact,
        "needs_review": needs_review,
        "country_distribution": [
            {"country": r.country, "count": r.count} for r in country_dist
        ],
        "sector_distribution": [
            {"sector": r.industry, "count": r.count} for r in sector_dist
        ],
        "type_distribution": [
            {"type": r.signal_type.value if hasattr(r.signal_type, 'value') else r.signal_type,
             "count": r.count} for r in type_dist
        ],
    }


def _signal_to_dict(signal: Signal, db: Session) -> dict:
    """Signal model'ini dict'e çevir."""
    article = db.query(Article).get(signal.article_id) if signal.article_id else None
    source = db.query(Source).get(article.source_id) if article and article.source_id else None

    return {
        "id": signal.id,
        "article_id": signal.article_id,
        "detected_company": signal.detected_company,
        "industry": signal.industry,
        "country": signal.country,
        "city_or_region": signal.city_or_region,
        "signal_type": signal.signal_type.value if hasattr(signal.signal_type, 'value') else signal.signal_type,
        "signal_type_label_tr": signal.signal_type_label_tr,
        "summary_tr": signal.summary_tr,
        "confidence_score": signal.confidence_score,
        "impact_score": signal.impact_score,
        "composite_score": signal.composite_score,
        "evidence_phrases": signal.evidence_phrases or [],
        "relevant_sectors": signal.relevant_sectors or [],
        "keywords_matched": signal.keywords_matched or [],
        "review_status": signal.review_status.value if hasattr(signal.review_status, 'value') else signal.review_status,
        "is_duplicate": signal.is_duplicate,
        "duplicate_group_id": signal.duplicate_group_id,
        "detection_method": signal.detection_method,
        "ai_model_used": signal.ai_model_used,
        "created_at": signal.created_at.isoformat() if signal.created_at else None,
        "article_title": article.title if article else None,
        "article_url": article.url if article else None,
        "article_published_at": article.published_at.isoformat() if article and article.published_at else None,
        "source_name": source.name if source else None,
        "source_country": source.country if source else None,
    }
