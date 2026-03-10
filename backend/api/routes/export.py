"""
Veri export endpoint'leri (JSON, CSV).
"""
import csv
import io
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.db.database import get_db
from backend.db.models import Signal, Article, Source

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/signals/json")
def export_signals_json(
    days: int = Query(7, ge=1, le=90),
    min_score: float = Query(0.3, ge=0, le=1),
    db: Session = Depends(get_db),
):
    """Sinyalleri JSON olarak export et."""
    since = datetime.utcnow() - timedelta(days=days)

    signals = (
        db.query(Signal)
        .filter(Signal.created_at >= since)
        .filter(Signal.composite_score >= min_score)
        .filter(Signal.is_duplicate == False)
        .order_by(desc(Signal.composite_score))
        .all()
    )

    data = []
    for sig in signals:
        article = db.query(Article).get(sig.article_id) if sig.article_id else None
        source = db.query(Source).get(article.source_id) if article and article.source_id else None

        data.append({
            "id": sig.id,
            "signal_type": sig.signal_type.value if hasattr(sig.signal_type, 'value') else sig.signal_type,
            "signal_type_tr": sig.signal_type_label_tr,
            "company": sig.detected_company,
            "industry": sig.industry,
            "country": sig.country,
            "region": sig.city_or_region,
            "summary_tr": sig.summary_tr,
            "confidence": sig.confidence_score,
            "impact": sig.impact_score,
            "composite": sig.composite_score,
            "evidence": sig.evidence_phrases,
            "article_url": article.url if article else None,
            "article_title": article.title if article else None,
            "source": source.name if source else None,
            "detected_at": sig.created_at.isoformat() if sig.created_at else None,
        })

    return JSONResponse(
        content={"signals": data, "count": len(data), "exported_at": datetime.utcnow().isoformat()},
        headers={"Content-Disposition": f"attachment; filename=signals_{datetime.now().strftime('%Y%m%d')}.json"}
    )


@router.get("/signals/csv")
def export_signals_csv(
    days: int = Query(7, ge=1, le=90),
    min_score: float = Query(0.3, ge=0, le=1),
    db: Session = Depends(get_db),
):
    """Sinyalleri CSV olarak export et."""
    since = datetime.utcnow() - timedelta(days=days)

    signals = (
        db.query(Signal)
        .filter(Signal.created_at >= since)
        .filter(Signal.composite_score >= min_score)
        .filter(Signal.is_duplicate == False)
        .order_by(desc(Signal.composite_score))
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "ID", "Sinyal Tipi", "Sinyal Tipi (TR)", "Şirket", "Sektör",
        "Ülke", "Bölge", "Özet", "Güven Skoru", "Etki Skoru",
        "Bileşik Skor", "Makale URL", "Kaynak", "Tespit Tarihi"
    ])

    for sig in signals:
        article = db.query(Article).get(sig.article_id) if sig.article_id else None
        source = db.query(Source).get(article.source_id) if article and article.source_id else None

        writer.writerow([
            sig.id,
            sig.signal_type.value if hasattr(sig.signal_type, 'value') else sig.signal_type,
            sig.signal_type_label_tr or "",
            sig.detected_company or "",
            sig.industry or "",
            sig.country or "",
            sig.city_or_region or "",
            (sig.summary_tr or "")[:200],
            f"{sig.confidence_score:.3f}",
            f"{sig.impact_score:.3f}",
            f"{sig.composite_score:.3f}",
            article.url if article else "",
            source.name if source else "",
            sig.created_at.strftime("%Y-%m-%d %H:%M") if sig.created_at else "",
        ])

    output.seek(0)
    filename = f"opensignal_export_{datetime.now().strftime('%Y%m%d')}.csv"

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
