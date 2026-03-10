"""
Sistem yönetim API endpoint'leri.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from backend.db.database import get_db
from backend.db.models import SystemLog, AppSettings, Source, Article, Signal
from backend.ai.ollama_client import ollama

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status")
def get_system_status(db: Session = Depends(get_db)):
    """Sistem durumu ve istatistikler."""
    source_count = db.query(func.count(Source.id)).filter(Source.is_active == True).scalar()
    article_count = db.query(func.count(Article.id)).scalar()
    signal_count = db.query(func.count(Signal.id)).scalar()
    pending_count = db.query(func.count(Article.id)).filter(Article.is_processed == False).scalar()

    # Son log
    last_ingest = (
        db.query(SystemLog)
        .filter(SystemLog.event_type == "ingestion_run")
        .order_by(desc(SystemLog.created_at))
        .first()
    )

    # Ollama durumu
    ollama_status = {
        "enabled": ollama.is_available(),
        "model": ollama.model if ollama.is_available() else None,
        "base_url": ollama.base_url,
    }

    from backend.core.scheduler import scheduler
    jobs = []
    if scheduler.running:
        for job in scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            })

    return {
        "app_name": "OpenSignal Radar TR",
        "version": "1.0.0",
        "status": "operational",
        "database": {
            "active_sources": source_count,
            "total_articles": article_count,
            "total_signals": signal_count,
            "pending_processing": pending_count,
        },
        "scheduler": {
            "running": scheduler.running,
            "jobs": jobs,
        },
        "ollama": ollama_status,
        "last_ingestion": {
            "at": last_ingest.created_at.isoformat() if last_ingest else None,
            "summary": last_ingest.message if last_ingest else "Henüz çalışmadı",
        },
        "server_time": datetime.utcnow().isoformat(),
    }


@router.get("/logs")
def get_logs(
    page: int = 1,
    per_page: int = 50,
    event_type: str = None,
    db: Session = Depends(get_db),
):
    """Sistem logları."""
    query = db.query(SystemLog)
    if event_type:
        query = query.filter(SystemLog.event_type == event_type)

    total = query.count()
    logs = (
        query
        .order_by(desc(SystemLog.created_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return {
        "items": [
            {
                "id": log.id,
                "event_type": log.event_type,
                "message": log.message,
                "level": log.level,
                "details": log.details,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
        "total": total,
    }


@router.post("/run-ingestion")
def trigger_full_ingestion(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Tüm kaynaklar için veri toplamayı başlat."""
    background_tasks.add_task(_run_full_pipeline)
    return {"success": True, "message": "Tam pipeline başlatıldı"}


@router.post("/run-processing")
def trigger_processing(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Bekleyen makalelerin sinyal işlemesini başlat."""
    background_tasks.add_task(_run_processing_only)
    return {"success": True, "message": "Sinyal işleme başlatıldı"}


@router.delete("/reset-ollama-cache")
def reset_ollama_cache():
    """Ollama erişilebilirlik cache'ini sıfırla."""
    ollama.reset_cache()
    return {"success": True, "available": ollama.is_available()}


def _log_pipeline_result(db, event_type: str, new_articles: int, new_signals: int):
    """Pipeline sonucunu SystemLog'a kaydet."""
    from backend.db.models import SystemLog
    log = SystemLog(
        event_type=event_type,
        level="INFO",
        message=f"{new_articles} makale, {new_signals} yeni sinyal",
        details={"new_articles": new_articles, "new_signals": new_signals},
        created_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()


def _run_full_pipeline():
    """Background: ingest + process."""
    from backend.db.database import SessionLocal
    from backend.ingestion.orchestrator import IngestionOrchestrator
    from backend.signals.processor import SignalProcessor
    from sqlalchemy import func
    from backend.db.models import Article, Signal

    db = SessionLocal()
    try:
        articles_before = db.query(func.count(Article.id)).scalar()
        signals_before = db.query(func.count(Signal.id)).scalar()

        orchestrator = IngestionOrchestrator(db)
        orchestrator.run_all()

        processor = SignalProcessor(db)
        processor.process_pending_articles(limit=200)

        articles_after = db.query(func.count(Article.id)).scalar()
        signals_after = db.query(func.count(Signal.id)).scalar()

        _log_pipeline_result(
            db, "ingestion_run",
            new_articles=articles_after - articles_before,
            new_signals=signals_after - signals_before,
        )
    finally:
        db.close()


def _run_processing_only():
    """Background: sadece sinyal işleme."""
    from backend.db.database import SessionLocal
    from backend.signals.processor import SignalProcessor
    from sqlalchemy import func
    from backend.db.models import Signal

    db = SessionLocal()
    try:
        signals_before = db.query(func.count(Signal.id)).scalar()

        processor = SignalProcessor(db)
        processor.process_pending_articles(limit=200)

        signals_after = db.query(func.count(Signal.id)).scalar()

        _log_pipeline_result(
            db, "processing_run",
            new_articles=0,
            new_signals=signals_after - signals_before,
        )
    finally:
        db.close()
