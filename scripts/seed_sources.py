"""
Başlangıç kaynaklarını veritabanına yükler.
Gerçek dünya haber kaynakları, RSS feed'leri ve devlet duyuru sayfaları.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db.database import SessionLocal, init_db
from backend.db.models import Source, SourceType


SEED_SOURCES = [
    # ── Global Haber Kaynakları (RSS) ────────────────────────────────────────
    {
        "name": "Reuters - Business",
        "base_url": "https://www.reuters.com/business",
        "feed_url": "https://feeds.reuters.com/reuters/businessNews",
        "source_type": "rss",
        "country": "Global",
        "language": "en",
        "trust_score": 0.95,
        "priority_score": 0.90,
        "notes": "En güvenilir küresel haber kaynağı. M&A, yatırım haberleri.",
    },
    {
        "name": "Reuters - Technology",
        "base_url": "https://www.reuters.com/technology",
        "feed_url": "https://feeds.reuters.com/reuters/technologyNews",
        "source_type": "rss",
        "country": "Global",
        "language": "en",
        "trust_score": 0.95,
        "priority_score": 0.85,
    },
    {
        "name": "Bloomberg Industry",
        "base_url": "https://www.bloomberg.com/industries",
        "feed_url": "https://feeds.bloomberg.com/industries/news.rss",
        "source_type": "rss",
        "country": "Global",
        "language": "en",
        "trust_score": 0.90,
        "priority_score": 0.85,
    },
    {
        "name": "Financial Times",
        "base_url": "https://www.ft.com",
        "feed_url": "https://www.ft.com/rss/home/uk",
        "source_type": "rss",
        "country": "Global",
        "language": "en",
        "trust_score": 0.92,
        "priority_score": 0.82,
    },

    # ── Endüstri ve Sektör Haberleri ─────────────────────────────────────────
    {
        "name": "Electrek - EV & Energy",
        "base_url": "https://electrek.co",
        "feed_url": "https://electrek.co/feed/",
        "source_type": "rss",
        "country": "Global",
        "language": "en",
        "trust_score": 0.80,
        "priority_score": 0.85,
        "notes": "Elektrikli araç ve enerji yatırımları için güçlü kaynak.",
    },
    {
        "name": "PV Tech - Solar",
        "base_url": "https://www.pv-tech.org",
        "feed_url": "https://www.pv-tech.org/feed/",
        "source_type": "rss",
        "country": "Global",
        "language": "en",
        "trust_score": 0.85,
        "priority_score": 0.80,
        "notes": "Güneş enerjisi yatırımları.",
    },
    {
        "name": "Semiconductor Engineering",
        "base_url": "https://semiengineering.com",
        "feed_url": "https://semiengineering.com/feed/",
        "source_type": "rss",
        "country": "Global",
        "language": "en",
        "trust_score": 0.85,
        "priority_score": 0.90,
        "notes": "Yarı iletken ve çip üretim haberleri.",
    },
    {
        "name": "Tom's Hardware",
        "base_url": "https://www.tomshardware.com",
        "feed_url": "https://www.tomshardware.com/feeds/all",
        "source_type": "rss",
        "country": "Global",
        "language": "en",
        "trust_score": 0.78,
        "priority_score": 0.70,
    },
    {
        "name": "Mining Technology",
        "base_url": "https://www.mining-technology.com",
        "feed_url": "https://www.mining-technology.com/feed/",
        "source_type": "rss",
        "country": "Global",
        "language": "en",
        "trust_score": 0.82,
        "priority_score": 0.80,
        "notes": "Madencilik ve hammadde yatırımları.",
    },
    {
        "name": "Data Center Dynamics",
        "base_url": "https://www.datacenterdynamics.com",
        "feed_url": "https://www.datacenterdynamics.com/rss/",
        "source_type": "rss",
        "country": "Global",
        "language": "en",
        "trust_score": 0.88,
        "priority_score": 0.88,
        "notes": "Veri merkezi yatırımları için kritik kaynak.",
    },
    {
        "name": "Automotive News",
        "base_url": "https://www.autonews.com",
        "feed_url": "https://www.autonews.com/rss.xml",
        "source_type": "rss",
        "country": "Global",
        "language": "en",
        "trust_score": 0.88,
        "priority_score": 0.82,
        "notes": "Otomotiv üretim yatırımları.",
    },
    {
        "name": "Logistics Management",
        "base_url": "https://www.logisticsmgmt.com",
        "feed_url": "https://www.logisticsmgmt.com/rss/lm_breaking.xml",
        "source_type": "rss",
        "country": "Global",
        "language": "en",
        "trust_score": 0.78,
        "priority_score": 0.72,
    },

    # ── Türkiye — Genel Sanayi & Ekonomi ────────────────────────────────────
    {
        "name": "AA Ekonomi",
        "base_url": "https://www.aa.com.tr/tr/ekonomi",
        "feed_url": "https://www.aa.com.tr/tr/rss/default?cat=ekonomi",
        "source_type": "rss",
        "country": "Türkiye",
        "language": "tr",
        "trust_score": 0.80,
        "priority_score": 0.85,
        "notes": "Anadolu Ajansı ekonomi haberleri. Türkiye yatırım duyuruları.",
    },
    {
        "name": "Dünya Gazetesi",
        "base_url": "https://www.dunya.com",
        "feed_url": "https://www.dunya.com/rss",
        "source_type": "rss",
        "country": "Türkiye",
        "language": "tr",
        "trust_score": 0.82,
        "priority_score": 0.82,
        "notes": "Türkiye iş dünyası. Yatırım, teşvik haberleri.",
    },
    {
        "name": "Bloomberg HT",
        "base_url": "https://www.bloomberght.com",
        "feed_url": "https://www.bloomberght.com/rss",
        "source_type": "rss",
        "country": "Türkiye",
        "language": "tr",
        "trust_score": 0.85,
        "priority_score": 0.88,
    },
    {
        "name": "Cumhuriyet Ekonomi",
        "base_url": "https://www.cumhuriyet.com.tr/ekonomi",
        "feed_url": "https://www.cumhuriyet.com.tr/rss/ekonomi",
        "source_type": "rss",
        "country": "Türkiye",
        "language": "tr",
        "trust_score": 0.75,
        "priority_score": 0.70,
    },
    {
        "name": "Invest in Turkey (ISPAT)",
        "base_url": "https://www.invest.gov.tr",
        "feed_url": None,
        "source_type": "government",
        "country": "Türkiye",
        "language": "en",
        "trust_score": 0.90,
        "priority_score": 0.88,
        "notes": "Türkiye yatırım ajansı. Teşvik duyuruları.",
    },
    {
        "name": "Hürriyet Ekonomi",
        "base_url": "https://www.hurriyet.com.tr/ekonomi",
        "feed_url": "https://www.hurriyet.com.tr/rss/ekonomi",
        "source_type": "rss",
        "country": "Türkiye",
        "language": "tr",
        "trust_score": 0.78,
        "priority_score": 0.80,
        "notes": "Büyük yatırım duyuruları ve fabrika açılışları.",
    },
    {
        "name": "Sabah Ekonomi",
        "base_url": "https://www.sabah.com.tr/ekonomi",
        "feed_url": "https://www.sabah.com.tr/rss/ekonomi.xml",
        "source_type": "rss",
        "country": "Türkiye",
        "language": "tr",
        "trust_score": 0.75,
        "priority_score": 0.75,
    },
    {
        "name": "Milliyet Ekonomi",
        "base_url": "https://www.milliyet.com.tr/ekonomi",
        "feed_url": "https://www.milliyet.com.tr/rss/rssNew/ekonomiRss.xml",
        "source_type": "rss",
        "country": "Türkiye",
        "language": "tr",
        "trust_score": 0.75,
        "priority_score": 0.72,
    },

    # ── Türkiye — Sanayi & Endüstri Odaklı ──────────────────────────────────
    {
        "name": "MM Endüstri Dergisi",
        "base_url": "https://www.mm-industrie.com.tr",
        "feed_url": "https://www.mm-industrie.com.tr/feed/",
        "source_type": "rss",
        "country": "Türkiye",
        "language": "tr",
        "trust_score": 0.85,
        "priority_score": 0.92,
        "notes": "Türkiye imalat ve makina sektörü. TRENG için en kritik kaynak.",
    },
    {
        "name": "Makina.com.tr",
        "base_url": "https://www.makina.com.tr",
        "feed_url": "https://www.makina.com.tr/rss/haberler",
        "source_type": "rss",
        "country": "Türkiye",
        "language": "tr",
        "trust_score": 0.82,
        "priority_score": 0.90,
        "notes": "Makina sektörü haberleri. Konveyör, fan, filtrasyon haberleri için.",
    },
    {
        "name": "Sektoral Haber",
        "base_url": "https://www.sektoral.net",
        "feed_url": "https://www.sektoral.net/feed/",
        "source_type": "rss",
        "country": "Türkiye",
        "language": "tr",
        "trust_score": 0.78,
        "priority_score": 0.85,
        "notes": "Türk endüstri sektörü haberleri.",
    },
    {
        "name": "SanayiGündem",
        "base_url": "https://www.sanayigundem.com",
        "feed_url": "https://www.sanayigundem.com/feed/",
        "source_type": "rss",
        "country": "Türkiye",
        "language": "tr",
        "trust_score": 0.80,
        "priority_score": 0.88,
        "notes": "Türk sanayii yatırım haberleri. Fabrika açılışları, tesis yatırımları.",
    },
    {
        "name": "Enerji Gazetesi",
        "base_url": "https://www.enerjigazetesi.com",
        "feed_url": "https://www.enerjigazetesi.com/feed/",
        "source_type": "rss",
        "country": "Türkiye",
        "language": "tr",
        "trust_score": 0.82,
        "priority_score": 0.88,
        "notes": "Türkiye enerji santrali ve altyapı yatırımları. İRDA için kritik.",
    },
    {
        "name": "Petrol Ofisi Haberleri",
        "base_url": "https://www.petrolhaberleri.com",
        "feed_url": "https://www.petrolhaberleri.com/feed/",
        "source_type": "rss",
        "country": "Türkiye",
        "language": "tr",
        "trust_score": 0.78,
        "priority_score": 0.85,
        "notes": "Petrol, gaz, rafineri yatırımları. İRDA için kritik.",
    },
    {
        "name": "İnşaat Haberleri",
        "base_url": "https://www.insaathaberleri.com",
        "feed_url": "https://www.insaathaberleri.com/feed/",
        "source_type": "rss",
        "country": "Türkiye",
        "language": "tr",
        "trust_score": 0.78,
        "priority_score": 0.88,
        "notes": "Büyük inşaat projeleri, taahhüt haberleri. İRDA için kritik.",
    },
    {
        "name": "Çelik Konstrüksiyon Derneği",
        "base_url": "https://www.celtinsaat.com.tr",
        "feed_url": None,
        "source_type": "news_site",
        "country": "Türkiye",
        "language": "tr",
        "trust_score": 0.82,
        "priority_score": 0.80,
        "notes": "Çelik yapı ve konstrüksiyon sektörü haberleri.",
    },
    {
        "name": "Haber Ekspres Sanayi",
        "base_url": "https://www.haberexpres.com/sanayi",
        "feed_url": "https://www.haberexpres.com/rss",
        "source_type": "rss",
        "country": "Türkiye",
        "language": "tr",
        "trust_score": 0.72,
        "priority_score": 0.75,
    },
    {
        "name": "TAYSAD (Otomotiv Yan Sanayi)",
        "base_url": "https://www.taysad.org.tr/haberler",
        "feed_url": "https://www.taysad.org.tr/rss",
        "source_type": "rss",
        "country": "Türkiye",
        "language": "tr",
        "trust_score": 0.88,
        "priority_score": 0.90,
        "notes": "Otomotiv yan sanayi yatırımları. TRENG için kritik boyahane/filtrasyon sinyalleri.",
    },
    {
        "name": "OSD (Otomotiv Sanayii Derneği)",
        "base_url": "https://www.osd.org.tr",
        "feed_url": "https://www.osd.org.tr/rss",
        "source_type": "rss",
        "country": "Türkiye",
        "language": "tr",
        "trust_score": 0.88,
        "priority_score": 0.88,
        "notes": "Ana otomotiv üreticileri kapasite ve yatırım haberleri.",
    },
    {
        "name": "Mobilya Dünyası",
        "base_url": "https://www.mobilyadunyasi.com",
        "feed_url": "https://www.mobilyadunyasi.com/feed/",
        "source_type": "rss",
        "country": "Türkiye",
        "language": "tr",
        "trust_score": 0.78,
        "priority_score": 0.85,
        "notes": "Mobilya & ahşap sektörü. Talaş/toz toplama sistemleri için birincil sektör.",
    },

    # ── Türkiye — Resmi & İhale Kaynakları ──────────────────────────────────
    {
        "name": "Resmi Gazete",
        "base_url": "https://www.resmigazete.gov.tr",
        "feed_url": "https://www.resmigazete.gov.tr/rss",
        "source_type": "government",
        "country": "Türkiye",
        "language": "tr",
        "trust_score": 0.98,
        "priority_score": 0.92,
        "notes": "Ruhsat, teşvik belgesi, ÇED duyuruları için birincil resmi kaynak.",
    },
    {
        "name": "Çevre Bakanlığı ÇED Duyuruları",
        "base_url": "https://www.csb.gov.tr/projeler/ced",
        "feed_url": None,
        "source_type": "government",
        "country": "Türkiye",
        "language": "tr",
        "trust_score": 0.99,
        "priority_score": 0.95,
        "notes": "ÇED başvuruları = yeni büyük tesis işareti. İRDA için kritik.",
    },
    {
        "name": "Kamu İhale Kurumu",
        "base_url": "https://www.ihale.gov.tr",
        "feed_url": None,
        "source_type": "tender",
        "country": "Türkiye",
        "language": "tr",
        "trust_score": 0.99,
        "priority_score": 0.95,
        "notes": "Kamu ihaleleri. Büyük inşaat ve enerji projeleri için kritik.",
    },

    # ── Avrupa Kaynakları ───────────────────────────────────────────────────
    {
        "name": "Handelsblatt Global",
        "base_url": "https://www.handelsblatt.com/english",
        "feed_url": "https://www.handelsblatt.com/contentexport/feed/english",
        "source_type": "rss",
        "country": "Almanya",
        "language": "en",
        "trust_score": 0.88,
        "priority_score": 0.80,
        "notes": "Almanya sanayi yatırımları.",
    },
    {
        "name": "Euractiv Industry",
        "base_url": "https://www.euractiv.com/section/economy-jobs",
        "feed_url": "https://www.euractiv.com/section/economy-jobs/feed/",
        "source_type": "rss",
        "country": "AB",
        "language": "en",
        "trust_score": 0.82,
        "priority_score": 0.78,
        "notes": "AB sanayi politikası ve yatırımlar.",
    },
    {
        "name": "Benchmark Mineral Intelligence",
        "base_url": "https://www.benchmarkminerals.com",
        "feed_url": "https://www.benchmarkminerals.com/feed/",
        "source_type": "rss",
        "country": "Global",
        "language": "en",
        "trust_score": 0.90,
        "priority_score": 0.88,
        "notes": "Batarya hammaddeleri, lityum, kobalt pazar analizi.",
    },

    # ── Yatırım / M&A ───────────────────────────────────────────────────────
    {
        "name": "Mergermarket",
        "base_url": "https://www.mergermarket.com/info/news",
        "feed_url": None,
        "source_type": "news_site",
        "country": "Global",
        "language": "en",
        "trust_score": 0.88,
        "priority_score": 0.82,
        "notes": "M&A haberleri. Satın alma sinyalleri için.",
    },
    {
        "name": "S&P Global Market Intelligence",
        "base_url": "https://www.spglobal.com/marketintelligence/en/news-insights/latest-news-headlines",
        "feed_url": "https://www.spglobal.com/marketintelligence/rss/mi.rss",
        "source_type": "rss",
        "country": "Global",
        "language": "en",
        "trust_score": 0.92,
        "priority_score": 0.85,
    },

    # ── Savunma ve Teknoloji ────────────────────────────────────────────────
    {
        "name": "Defense News",
        "base_url": "https://www.defensenews.com",
        "feed_url": "https://www.defensenews.com/rss/",
        "source_type": "rss",
        "country": "Global",
        "language": "en",
        "trust_score": 0.88,
        "priority_score": 0.80,
        "notes": "Savunma sanayi yatırımları.",
    },
    {
        "name": "TechCrunch",
        "base_url": "https://techcrunch.com",
        "feed_url": "https://techcrunch.com/feed/",
        "source_type": "rss",
        "country": "Global",
        "language": "en",
        "trust_score": 0.80,
        "priority_score": 0.72,
        "notes": "Teknoloji yatırımları, veri merkezi açılışları.",
    },
]


def seed():
    """Başlangıç kaynaklarını yükle."""
    init_db()
    db = SessionLocal()

    added = 0
    skipped = 0

    for source_data in SEED_SOURCES:
        existing = db.query(Source).filter(
            Source.base_url == source_data["base_url"]
        ).first()

        if existing:
            skipped += 1
            continue

        source = Source(
            name=source_data["name"],
            base_url=source_data["base_url"],
            feed_url=source_data.get("feed_url"),
            source_type=source_data.get("source_type", "news_site"),
            country=source_data.get("country"),
            language=source_data.get("language", "en"),
            trust_score=source_data.get("trust_score", 0.7),
            priority_score=source_data.get("priority_score", 0.7),
            notes=source_data.get("notes"),
            is_active=True,
        )
        db.add(source)
        added += 1

    db.commit()
    db.close()

    print(f"✓ Kaynak yükleme tamamlandı: {added} eklendi, {skipped} zaten mevcut")
    return added


if __name__ == "__main__":
    seed()
