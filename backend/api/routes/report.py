"""
Haftalık / Aylık İstihbarat Raporu API
TRENG Mühendislik & İRDA Yapı için yapılandırılmış rapor üretir.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import Signal, Article, Source, WatchListCompany, ReviewStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/report", tags=["report"])

# ─── Yaklaşan Türkiye Fuarları (manuel liste — periyodik güncelle) ────────────
UPCOMING_FAIRS = [
    {
        "name": "WIN TURKEY — Makina Teknolojileri",
        "dates": "15–18 Mayıs 2025",
        "location": "İstanbul, Tüyap",
        "sectors": ["Makina", "İmalat", "Endüstri"],
        "treng_reason": "Konveyör, fan ve havalandırma ekipman tedarikçileri katılıyor; potansiyel müşteri networkü.",
        "irda_reason": "Mekanik taahhüt ve ekipman tedarik zincirleri için önemli temas noktası.",
        "url": "https://www.winturkey.com.tr",
    },
    {
        "name": "ANKIROS — Döküm, Metal, Metalurji",
        "dates": "4–6 Eylül 2025",
        "location": "İstanbul, Tüyap",
        "sectors": ["Metalurji", "Döküm", "Metal İşleme"],
        "treng_reason": "Döküm ve metal işleme tesislerinde talaş/toz toplama sistemleri için birincil sektör.",
        "irda_reason": "Endüstriyel tesis inşaatı için potansiyel yatırımcı müşteriler.",
        "url": "https://www.ankiros.com",
    },
    {
        "name": "EURASIA WOOD — Ahşap İşleme Teknolojileri",
        "dates": "Kasım 2025",
        "location": "İstanbul, CNR Expo",
        "sectors": ["Ahşap", "Mobilya", "İmalat"],
        "treng_reason": "Ahşap talaşı ve toz toplama sistemleri için en kritik Türk fuarı.",
        "irda_reason": "Mobilya fabrikası yatırımcıları için networking.",
        "url": "https://www.cnrexpo.com",
    },
    {
        "name": "SOLAREX İstanbul — Güneş & Enerji",
        "dates": "Mart 2026",
        "location": "İstanbul, CNR Expo",
        "sectors": ["Enerji", "Güneş", "Yenilenebilir"],
        "treng_reason": "Güneş paneli üretim tesislerinde temiz oda havalandırma sistemleri.",
        "irda_reason": "Enerji santrali ve altyapı yatırımcılarıyla doğrudan temas.",
        "url": "https://www.solarex.com.tr",
    },
    {
        "name": "YEMEK FUAR — Gıda Teknolojileri",
        "dates": "Nisan 2026",
        "location": "İstanbul, CNR Expo",
        "sectors": ["Gıda", "İçecek", "Ambalaj"],
        "treng_reason": "Gıda üretim tesislerinde hijyenik havalandırma ve toz kontrol sistemleri.",
        "irda_reason": "Gıda fabrikası ve depo inşaatı projeleri için yatırımcı ağı.",
        "url": "https://www.cnrexpo.com",
    },
    {
        "name": "MAKTEK KONYA — İmalat Teknolojileri",
        "dates": "Ekim 2026",
        "location": "Konya",
        "sectors": ["Makina", "İmalat", "Orta Anadolu Sanayi"],
        "treng_reason": "Konya OSB bölgesindeki üretim tesisleri için doğrudan erişim.",
        "irda_reason": "Orta Anadolu büyük yatırım projeleri takibi.",
        "url": "https://www.maktek.com.tr",
    },
    {
        "name": "BORU-VANA-FİTİNGS FUARI",
        "dates": "Mayıs 2026",
        "location": "İstanbul, Tüyap",
        "sectors": ["Boru", "Vana", "Altyapı"],
        "treng_reason": "Endüstriyel kanallama ve hava dağıtım hatları için tedarikçi ağı.",
        "irda_reason": "Petrol & gaz ve enerji altyapısı için kritik malzeme tedarikçileri.",
        "url": "https://www.tuyap.com.tr",
    },
    {
        "name": "AUTOMECHANIKA İSTANBUL",
        "dates": "Haziran 2026",
        "location": "İstanbul, Tüyap",
        "sectors": ["Otomotiv", "Yan Sanayi"],
        "treng_reason": "Otomotiv yan sanayi boyahane ve filtrasyon ekipmanları için en önemli Türk fuarı.",
        "irda_reason": "Otomotiv fabrikası genişleme yatırımları için yatırımcı ağı.",
        "url": "https://www.automechanika-istanbul.com",
    },
    {
        "name": "TÜYAP İNŞAAT FUARI",
        "dates": "Ekim 2026",
        "location": "İstanbul, Tüyap",
        "sectors": ["İnşaat", "Yapı", "Altyapı"],
        "treng_reason": "Büyük tesis inşaatları için havalandırma sistem kararları bu fuarda şekillenir.",
        "irda_reason": "Müteahhit ve yüklenici ağı, ihale bilgisi ve proje ortaklıkları.",
        "url": "https://www.tuyap.com.tr",
    },
]


def _serialize_signal(sig: Signal) -> dict:
    article = sig.article
    source = article.source if article else None
    return {
        "id": sig.id,
        "company": sig.detected_company,
        "country": sig.country,
        "city": sig.city_or_region,
        "signal_type": sig.signal_type_label_tr or sig.signal_type,
        "summary_tr": sig.summary_tr,
        "evidence": (sig.evidence_phrases or [])[:2],
        "treng_score": sig.treng_score or 0,
        "irda_score": sig.irda_score or 0,
        "confidence": round((sig.confidence_score or 0) * 100),
        "impact": round((sig.impact_score or 0) * 100),
        "composite": round((sig.composite_score or 0) * 100),
        "matched_watchlist": sig.matched_watchlist or [],
        "article_title": article.title if article else None,
        "article_url": article.url if article else None,
        "article_date": article.published_at.strftime("%d.%m.%Y") if (article and article.published_at) else None,
        "source_name": source.name if source else None,
        "created_at": sig.created_at.isoformat() if sig.created_at else None,
    }


def _generate_ai_summary(signals_data: dict, days: int) -> Optional[str]:
    """Groq ile yönetici özeti üret."""
    try:
        from backend.ai.groq_client import groq
        if not groq.is_available():
            return None

        treng_count = len(signals_data["treng_top"])
        irda_count = len(signals_data["irda_top"])
        watch_count = len(signals_data["watch"])
        period = f"son {days} gün"

        # En kritik 3 gelişmeyi özetle
        top3 = []
        all_top = (signals_data["treng_top"] + signals_data["irda_top"])[:6]
        for s in all_top[:3]:
            top3.append(f"- {s.get('company', 'Bilinmiyor')}: {s.get('summary_tr', '')[:150]}")

        top3_text = "\n".join(top3) if top3 else "- Kritik gelişme tespit edilmedi."

        prompt = f"""Aşağıdaki endüstriyel istihbarat verilerini kullanarak yönetici özeti yaz.

Dönem: {period}
TRENG için anlamlı sinyal: {treng_count}
İRDA için anlamlı sinyal: {irda_count}
Takipte olan (zayıf kanıt): {watch_count}

En kritik gelişmeler:
{top3_text}

Görevin: Maksimum 8 satır, Türkçe, net ve aksiyonel yönetici özeti yaz.
- Kaç sinyal bulundu
- En kritik 2-3 gelişmeyi belirt
- TRENG ve İRDA açısından bu haftanın önemi
- Sonuçta tek cümle öneri

Sadece özeti yaz, başlık veya madde işareti ekleme."""

        return groq.generate(prompt, max_tokens=350)
    except Exception as e:
        logger.warning(f"AI özet hatası: {e}")
        return None


@router.get("/generate")
def generate_report(
    days: int = Query(default=7, ge=1, le=120),
    treng_min: float = Query(default=20.0),
    irda_min: float = Query(default=20.0),
    include_rejected: bool = False,
    db: Session = Depends(get_db),
):
    """
    Belirtilen gün aralığı için TRENG & İRDA raporu üret.
    """
    since = datetime.utcnow() - timedelta(days=days)

    # Temel sinyal sorgusu
    q = (
        db.query(Signal)
        .join(Article, Signal.article_id == Article.id)
        .filter(Signal.created_at >= since)
        .filter(Signal.is_duplicate == False)
    )
    if not include_rejected:
        q = q.filter(Signal.review_status != ReviewStatus.REJECTED)

    all_signals = q.order_by(Signal.composite_score.desc()).all()

    # Takip listesi firmaları
    watchlist_count = db.query(WatchListCompany).filter(WatchListCompany.is_active == True).count()

    # TRENG için önemli sinyaller (treng_score >= min, en fazla 5)
    treng_signals = [
        s for s in all_signals
        if (s.treng_score or 0) >= treng_min
    ]
    treng_signals.sort(key=lambda s: s.treng_score or 0, reverse=True)
    treng_top = treng_signals[:5]

    # İRDA için önemli sinyaller
    irda_signals = [
        s for s in all_signals
        if (s.irda_score or 0) >= irda_min
    ]
    irda_signals.sort(key=lambda s: s.irda_score or 0, reverse=True)
    irda_top = irda_signals[:5]

    # Takipte olanlar: orta eşiğin altında ama sıfır değil
    watch_threshold_treng = treng_min * 0.5
    watch_threshold_irda = irda_min * 0.5
    watch_signals = [
        s for s in all_signals
        if (
            (watch_threshold_treng <= (s.treng_score or 0) < treng_min) or
            (watch_threshold_irda <= (s.irda_score or 0) < irda_min)
        )
    ]
    watch_signals.sort(key=lambda s: max(s.treng_score or 0, s.irda_score or 0), reverse=True)
    watch_top = watch_signals[:8]

    # Takip listesiyle eşleşen sinyaller
    matched_signals = [s for s in all_signals if s.matched_watchlist]
    matched_signals.sort(key=lambda s: max(s.treng_score or 0, s.irda_score or 0), reverse=True)

    # Serialize
    signals_data = {
        "treng_top": [_serialize_signal(s) for s in treng_top],
        "irda_top": [_serialize_signal(s) for s in irda_top],
        "watch": [_serialize_signal(s) for s in watch_top],
        "matched_watchlist": [_serialize_signal(s) for s in matched_signals[:10]],
    }

    # AI yönetici özeti
    ai_summary = _generate_ai_summary(signals_data, days)

    # Fallback özet
    if not ai_summary:
        ai_summary = (
            f"Son {days} günde TRENG için {len(treng_signals)}, "
            f"İRDA için {len(irda_signals)} anlamlı sinyal tespit edildi. "
            f"Takip listesinde {watchlist_count} firma izleniyor."
        )
        if not treng_signals and not irda_signals:
            ai_summary = (
                f"Son {days} gün içinde TRENG veya İRDA için "
                f"doğrulanmış operasyonel sinyal bulunamadı. "
                f"Daha geniş bir zaman aralığı seçin veya eşiği düşürün."
            )

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "period_days": days,
        "since": since.strftime("%d.%m.%Y"),
        "until": datetime.utcnow().strftime("%d.%m.%Y"),
        "thresholds": {"treng": treng_min, "irda": irda_min},
        "stats": {
            "total_signals": len(all_signals),
            "treng_signals": len(treng_signals),
            "irda_signals": len(irda_signals),
            "watch_signals": len(watch_signals),
            "matched_watchlist": len(matched_signals),
            "watchlist_count": watchlist_count,
        },
        "executive_summary": ai_summary,
        "treng_findings": signals_data["treng_top"],
        "irda_findings": signals_data["irda_top"],
        "watchlist_matches": signals_data["matched_watchlist"],
        "watch_later": signals_data["watch"],
        "fair_radar": UPCOMING_FAIRS,
    }


@router.get("/fairs")
def get_fairs():
    """Yaklaşan fuar listesi."""
    return {"fairs": UPCOMING_FAIRS}
