"""
Kaynak yönetimi API endpoint'leri.
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel, HttpUrl

from backend.db.database import get_db
from backend.db.models import Source, SourceType

router = APIRouter(prefix="/api/sources", tags=["sources"])


class SourceCreate(BaseModel):
    name: str
    base_url: str
    feed_url: Optional[str] = None
    source_type: str = "news_site"
    country: Optional[str] = None
    language: str = "en"
    priority_score: float = 0.5
    trust_score: float = 0.5
    check_interval_hours: float = 2.0
    notes: Optional[str] = None


class SourceUpdate(BaseModel):
    name: Optional[str] = None
    feed_url: Optional[str] = None
    source_type: Optional[str] = None
    country: Optional[str] = None
    priority_score: Optional[float] = None
    trust_score: Optional[float] = None
    is_active: Optional[bool] = None
    check_interval_hours: Optional[float] = None
    notes: Optional[str] = None


@router.get("/", response_model=dict)
def list_sources(
    page: int = 1,
    per_page: int = 50,
    is_active: Optional[bool] = None,
    source_type: Optional[str] = None,
    country: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Kaynak listesi."""
    query = db.query(Source)

    if is_active is not None:
        query = query.filter(Source.is_active == is_active)
    if source_type:
        query = query.filter(Source.source_type == source_type)
    if country:
        query = query.filter(Source.country.ilike(f"%{country}%"))

    total = query.count()
    sources = (
        query
        .order_by(desc(Source.priority_score))
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    from sqlalchemy import func
    # Her kaynak için makale sayısı
    items = []
    for src in sources:
        from backend.db.models import Article, Signal
        article_count = (
            db.query(func.count(Article.id))
            .filter(Article.source_id == src.id)
            .scalar()
        )
        items.append({
            "id": src.id,
            "name": src.name,
            "base_url": src.base_url,
            "feed_url": src.feed_url,
            "source_type": src.source_type.value if hasattr(src.source_type, 'value') else src.source_type,
            "country": src.country,
            "language": src.language,
            "priority_score": src.priority_score,
            "trust_score": src.trust_score,
            "is_active": src.is_active,
            "last_checked_at": src.last_checked_at.isoformat() if src.last_checked_at else None,
            "check_interval_hours": src.check_interval_hours,
            "notes": src.notes,
            "article_count": article_count,
            "created_at": src.created_at.isoformat() if src.created_at else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{source_id}")
def get_source(source_id: int, db: Session = Depends(get_db)):
    """Tek kaynak detayı."""
    source = db.query(Source).get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Kaynak bulunamadı")
    return _source_to_dict(source, db)


@router.post("/", status_code=201)
def create_source(data: SourceCreate, db: Session = Depends(get_db)):
    """Yeni kaynak ekle."""
    # Duplicate URL kontrolü
    existing = db.query(Source).filter(Source.base_url == data.base_url).first()
    if existing:
        raise HTTPException(status_code=409, detail="Bu URL zaten kayıtlı")

    source = Source(
        name=data.name,
        base_url=data.base_url,
        feed_url=data.feed_url,
        source_type=data.source_type,
        country=data.country,
        language=data.language,
        priority_score=data.priority_score,
        trust_score=data.trust_score,
        check_interval_hours=data.check_interval_hours,
        notes=data.notes,
        is_active=True,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return _source_to_dict(source, db)


@router.patch("/{source_id}")
def update_source(
    source_id: int,
    data: SourceUpdate,
    db: Session = Depends(get_db),
):
    """Kaynak güncelle."""
    source = db.query(Source).get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Kaynak bulunamadı")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(source, field, value)

    source.updated_at = datetime.utcnow()
    db.commit()
    return _source_to_dict(source, db)


@router.delete("/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db)):
    """Kaynağı pasifleştir (fiziksel silme yapma)."""
    source = db.query(Source).get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Kaynak bulunamadı")

    source.is_active = False
    db.commit()
    return {"success": True}


@router.post("/{source_id}/ingest")
def trigger_ingest(
    source_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Kaynağı hemen tara."""
    source = db.query(Source).get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Kaynak bulunamadı")

    background_tasks.add_task(_run_source_ingest, source_id)
    return {"success": True, "message": f"{source.name} tarama başlatıldı"}


def _run_source_ingest(source_id: int):
    """Background task: kaynak ingest."""
    from backend.db.database import SessionLocal
    from backend.ingestion.orchestrator import IngestionOrchestrator
    from backend.signals.processor import SignalProcessor

    db = SessionLocal()
    try:
        orchestrator = IngestionOrchestrator(db)
        orchestrator.run_source(source_id)

        processor = SignalProcessor(db)
        processor.process_pending_articles()
    finally:
        db.close()


def _source_to_dict(source: Source, db: Session) -> dict:
    from sqlalchemy import func
    from backend.db.models import Article
    article_count = (
        db.query(func.count(Article.id))
        .filter(Article.source_id == source.id)
        .scalar()
    )
    return {
        "id": source.id,
        "name": source.name,
        "base_url": source.base_url,
        "feed_url": source.feed_url,
        "source_type": source.source_type.value if hasattr(source.source_type, 'value') else source.source_type,
        "country": source.country,
        "language": source.language,
        "priority_score": source.priority_score,
        "trust_score": source.trust_score,
        "is_active": source.is_active,
        "last_checked_at": source.last_checked_at.isoformat() if source.last_checked_at else None,
        "check_interval_hours": source.check_interval_hours,
        "notes": source.notes,
        "article_count": article_count,
        "created_at": source.created_at.isoformat() if source.created_at else None,
    }
