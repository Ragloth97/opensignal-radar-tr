"""
OpenSignal Radar TR - Ana FastAPI uygulaması.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.core.logging import logger
from backend.db.database import init_db

# Route'ları import et
from backend.api.routes import signals, sources, trends, deck, system, export, watchlist, report

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "frontend" / "templates"
STATIC_DIR = BASE_DIR / "frontend" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama başlangıç ve kapanış işlemleri."""
    logger.info("OpenSignal Radar TR başlatılıyor...")

    # Veritabanını başlat
    init_db()
    logger.info("Veritabanı hazır")

    # Zamanlayıcıyı başlat
    from backend.core.scheduler import start_scheduler
    start_scheduler()

    yield

    # Kapanışta zamanlayıcıyı durdur
    from backend.core.scheduler import stop_scheduler
    stop_scheduler()
    logger.info("OpenSignal Radar TR kapatıldı")


app = FastAPI(
    title="OpenSignal Radar TR",
    description="Açık Kaynak Ekonomik Sinyal Tespit Platformu",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# API Router'ları ekle
app.include_router(signals.router)
app.include_router(sources.router)
app.include_router(trends.router)
app.include_router(deck.router)
app.include_router(system.router)
app.include_router(export.router)
app.include_router(watchlist.router)
app.include_router(report.router)


# ─── Frontend Sayfaları ──────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("pages/dashboard.html", {"request": request})


@app.get("/sinyaller", response_class=HTMLResponse)
async def signals_page(request: Request):
    return templates.TemplateResponse("pages/signals.html", {"request": request})


@app.get("/sinyaller/{signal_id}", response_class=HTMLResponse)
async def signal_detail(request: Request, signal_id: int):
    return templates.TemplateResponse(
        "pages/signal_detail.html",
        {"request": request, "signal_id": signal_id}
    )


@app.get("/kaynaklar", response_class=HTMLResponse)
async def sources_page(request: Request):
    return templates.TemplateResponse("pages/sources.html", {"request": request})


@app.get("/inceleme", response_class=HTMLResponse)
async def review_page(request: Request):
    return templates.TemplateResponse("pages/review.html", {"request": request})


@app.get("/trendler", response_class=HTMLResponse)
async def trends_page(request: Request):
    return templates.TemplateResponse("pages/trends.html", {"request": request})


@app.get("/briefing", response_class=HTMLResponse)
async def deck_page(request: Request):
    return templates.TemplateResponse("pages/deck.html", {"request": request})


@app.get("/ayarlar", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("pages/settings.html", {"request": request})


@app.get("/takip", response_class=HTMLResponse)
async def watchlist_page(request: Request):
    return templates.TemplateResponse("pages/watchlist.html", {"request": request})


@app.get("/rapor", response_class=HTMLResponse)
async def report_page(request: Request):
    return templates.TemplateResponse("pages/report.html", {"request": request})
