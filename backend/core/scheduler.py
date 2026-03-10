"""
APScheduler ile periyodik görev zamanlayıcı.
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from backend.core.config import settings

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")


def run_ingestion():
    """Periyodik veri toplama görevi."""
    from backend.db.database import SessionLocal
    from backend.ingestion.orchestrator import IngestionOrchestrator

    db = SessionLocal()
    try:
        orchestrator = IngestionOrchestrator(db)
        results = orchestrator.run_all()
        logger.info(f"Periyodik ingest: {results}")
    except Exception as e:
        logger.error(f"Periyodik ingest hatası: {e}")
    finally:
        db.close()


def run_signal_processing():
    """Periyodik sinyal işleme görevi."""
    from backend.db.database import SessionLocal
    from backend.signals.processor import SignalProcessor

    db = SessionLocal()
    try:
        processor = SignalProcessor(db)
        count = processor.process_pending_articles()
        logger.info(f"Periyodik sinyal işleme: {count} sinyal")
    except Exception as e:
        logger.error(f"Periyodik sinyal işleme hatası: {e}")
    finally:
        db.close()


def run_trend_analysis():
    """Periyodik trend analizi görevi."""
    from backend.db.database import SessionLocal
    from backend.signals.trends import TrendAnalyzer

    db = SessionLocal()
    try:
        analyzer = TrendAnalyzer(db)
        count = analyzer.run()
        logger.info(f"Periyodik trend analizi: {count} küme güncellendi")
    except Exception as e:
        logger.error(f"Periyodik trend analizi hatası: {e}")
    finally:
        db.close()


def start_scheduler():
    """Zamanlayıcıyı başlat ve görevleri ekle."""
    if scheduler.running:
        return

    # Veri toplama
    scheduler.add_job(
        run_ingestion,
        trigger=IntervalTrigger(hours=settings.INGESTION_INTERVAL_HOURS),
        id="ingestion",
        name="Veri Toplama",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Sinyal işleme (ingest'ten biraz sonra)
    scheduler.add_job(
        run_signal_processing,
        trigger=IntervalTrigger(hours=settings.SIGNAL_PROCESSING_INTERVAL_HOURS),
        id="signal_processing",
        name="Sinyal İşleme",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Trend analizi
    scheduler.add_job(
        run_trend_analysis,
        trigger=IntervalTrigger(hours=settings.TREND_CLUSTER_INTERVAL_HOURS),
        id="trend_analysis",
        name="Trend Analizi",
        replace_existing=True,
        misfire_grace_time=600,
    )

    scheduler.start()
    logger.info("Zamanlayıcı başlatıldı")


def stop_scheduler():
    """Zamanlayıcıyı durdur."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Zamanlayıcı durduruldu")
