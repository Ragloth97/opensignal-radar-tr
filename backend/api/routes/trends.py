"""
Trend ve kümelenme API endpoint'leri.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.db.database import get_db
from backend.db.models import TrendCluster, TrendClusterMembership

router = APIRouter(prefix="/api/trends", tags=["trends"])


@router.get("/", response_model=dict)
def list_trends(
    page: int = 1,
    per_page: int = 20,
    sector: Optional[str] = None,
    geography: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Aktif trend kümeleri."""
    query = (
        db.query(TrendCluster)
        .filter(TrendCluster.is_active == True)
    )

    if sector:
        query = query.filter(TrendCluster.sector == sector)
    if geography:
        query = query.filter(TrendCluster.geography.ilike(f"%{geography}%"))

    total = query.count()
    clusters = (
        query
        .order_by(desc(TrendCluster.cluster_score), desc(TrendCluster.signal_count))
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    items = [_cluster_to_dict(c, db) for c in clusters]

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{cluster_id}")
def get_trend(cluster_id: int, db: Session = Depends(get_db)):
    """Trend kümesi detayı."""
    from fastapi import HTTPException
    cluster = db.query(TrendCluster).get(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Küme bulunamadı")
    return _cluster_to_dict(cluster, db, include_signals=True)


@router.post("/analyze")
def trigger_trend_analysis(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Trend analizini hemen başlat."""
    background_tasks.add_task(_run_trend_analysis)
    return {"success": True, "message": "Trend analizi başlatıldı"}


def _run_trend_analysis():
    from backend.db.database import SessionLocal
    from backend.signals.trends import TrendAnalyzer
    db = SessionLocal()
    try:
        analyzer = TrendAnalyzer(db)
        analyzer.run()
    finally:
        db.close()


def _cluster_to_dict(
    cluster: TrendCluster,
    db: Session,
    include_signals: bool = False,
) -> dict:
    result = {
        "id": cluster.id,
        "label": cluster.label,
        "description_tr": cluster.description_tr,
        "sector": cluster.sector,
        "geography": cluster.geography,
        "cluster_score": cluster.cluster_score,
        "signal_count": cluster.signal_count,
        "is_active": cluster.is_active,
        "first_seen_at": cluster.first_seen_at.isoformat() if cluster.first_seen_at else None,
        "last_seen_at": cluster.last_seen_at.isoformat() if cluster.last_seen_at else None,
        "created_at": cluster.created_at.isoformat() if cluster.created_at else None,
    }

    if include_signals:
        from backend.db.models import Signal
        memberships = (
            db.query(TrendClusterMembership)
            .filter(TrendClusterMembership.cluster_id == cluster.id)
            .limit(10)
            .all()
        )
        signal_ids = [m.signal_id for m in memberships]
        signals = db.query(Signal).filter(Signal.id.in_(signal_ids)).all()
        result["signals"] = [
            {
                "id": s.id,
                "signal_type": s.signal_type.value if hasattr(s.signal_type, 'value') else s.signal_type,
                "signal_type_label_tr": s.signal_type_label_tr,
                "detected_company": s.detected_company,
                "country": s.country,
                "composite_score": s.composite_score,
                "summary_tr": s.summary_tr,
            }
            for s in signals
        ]

    return result
