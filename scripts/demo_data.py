"""
Demo veri oluşturucu.
Gerçek veri olmadan arayüzü test etmek için kullanılır.
"""
import sys
import os
import random
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db.database import SessionLocal, init_db
from backend.db.models import (
    Source, Article, Signal, TrendCluster,
    SignalType, ReviewStatus, SourceType
)


DEMO_SIGNALS = [
    {
        "article_title": "Samsung Announces $17 Billion Semiconductor Fab in Texas",
        "url": "https://demo.example.com/samsung-texas-fab-1",
        "company": "Samsung Electronics",
        "country": "ABD",
        "city": "Taylor, Texas",
        "industry": "yari_iletken",
        "signal_type": SignalType.SEMICONDUCTOR,
        "summary_tr": "Samsung Electronics, Texas eyaletinin Taylor şehrinde 17 milyar dolarlık yarı iletken üretim tesisi kuracağını açıkladı. Tesis, 2026 yılında üretime başlayacak ve 1.800 yüksek nitelikli iş olanağı yaratacak.",
        "confidence": 0.91,
        "impact": 0.88,
        "evidence": ["Samsung will build a $17 billion semiconductor fab in Taylor, Texas", "The facility will create 1,800 high-skilled jobs"],
    },
    {
        "article_title": "CATL to Build €7.3bn Battery Gigafactory in Hungary",
        "url": "https://demo.example.com/catl-hungary-gigafactory-2",
        "company": "CATL",
        "country": "Macaristan",
        "city": "Debrecen",
        "industry": "enerji",
        "signal_type": SignalType.NEW_FACILITY,
        "summary_tr": "Çin'in en büyük elektrikli araç bataryası üreticisi CATL, Macaristan'ın Debrecen şehrinde 7.3 milyar Euro'luk devasa bir gigafabrika inşa edeceğini duyurdu. Kapasite yılda 100 GWh olacak.",
        "confidence": 0.93,
        "impact": 0.92,
        "evidence": ["CATL to invest €7.3 billion in Debrecen gigafactory", "100 GWh annual production capacity"],
    },
    {
        "article_title": "Microsoft Commits to $2.2B Investment in Malaysian AI Infrastructure",
        "url": "https://demo.example.com/microsoft-malaysia-ai-3",
        "company": "Microsoft",
        "country": "Malezya",
        "city": "Kuala Lumpur",
        "industry": "veri_merkezi",
        "signal_type": SignalType.DATA_CENTER,
        "summary_tr": "Microsoft, Malezya'ya yapay zeka altyapısı için 2.2 milyar dolar yatırım yapacağını açıkladı. Yatırım kapsamında yeni veri merkezleri ve yerel yeteneklerin geliştirilmesi yer alıyor.",
        "confidence": 0.89,
        "impact": 0.85,
        "evidence": ["Microsoft announces $2.2 billion AI infrastructure investment in Malaysia", "New data centers to be built across the country"],
    },
    {
        "article_title": "Volkswagen Expands EV Production at Emden Plant",
        "url": "https://demo.example.com/vw-emden-expansion-4",
        "company": "Volkswagen AG",
        "country": "Almanya",
        "city": "Emden",
        "industry": "otomotiv",
        "signal_type": SignalType.EXPANSION,
        "summary_tr": "Volkswagen, Almanya'nın Emden fabrikasında elektrikli araç üretim kapasitesini artıracak. Yatırım miktarı 1.8 milyar Euro olarak açıklandı.",
        "confidence": 0.87,
        "impact": 0.82,
        "evidence": ["Volkswagen to expand EV production at Emden plant", "€1.8 billion capacity expansion investment"],
    },
    {
        "article_title": "Turkish Government Awards New Investment Incentives for EV Sector",
        "url": "https://demo.example.com/turkey-ev-incentives-5",
        "company": None,
        "country": "Türkiye",
        "city": "Ankara",
        "industry": "otomotiv",
        "signal_type": SignalType.INCENTIVE,
        "summary_tr": "Türkiye Hazine ve Maliye Bakanlığı, elektrikli araç sektörüne yönelik yeni yatırım teşvikleri paketini açıkladı. Teşvikler vergi indirimi ve arazi tahsisini kapsıyor.",
        "confidence": 0.85,
        "impact": 0.78,
        "evidence": ["Turkish government announces new EV investment incentives", "Tax breaks and land allocation for qualifying investments"],
    },
    {
        "article_title": "Rio Tinto Begins Construction of Lithium Mining Project in Serbia",
        "url": "https://demo.example.com/rio-tinto-serbia-lithium-6",
        "company": "Rio Tinto",
        "country": "Sırbistan",
        "city": "Jadar Valley",
        "industry": "madencilik",
        "signal_type": SignalType.MINING,
        "summary_tr": "Rio Tinto, Sırbistan'ın Jadar Vadisi'ndeki lityum madeni projesinde inşaata başladığını açıkladı. Proje tamamlandığında Avrupa'nın en büyük lityum üretim tesisi olacak.",
        "confidence": 0.88,
        "impact": 0.86,
        "evidence": ["Rio Tinto breaks ground at Jadar lithium mine", "Will become Europe's largest lithium production facility"],
    },
    {
        "article_title": "Amazon Web Services Opens New Data Center Region in Poland",
        "url": "https://demo.example.com/aws-poland-region-7",
        "company": "Amazon Web Services",
        "country": "Polonya",
        "city": "Warsaw",
        "industry": "veri_merkezi",
        "signal_type": SignalType.DATA_CENTER,
        "summary_tr": "Amazon Web Services, Polonya'da yeni bir bulut bölgesi açtığını duyurdu. Yatırım büyüklüğü 3 milyar USD olarak açıklanırken bölgenin 10 yılda 14.000 iş yaratması bekleniyor.",
        "confidence": 0.92,
        "impact": 0.88,
        "evidence": ["AWS opens new cloud region in Warsaw, Poland", "$3 billion investment creating 14,000 jobs over 10 years"],
    },
    {
        "article_title": "Bosch Hiring 3,000 Engineers for EV Component Division",
        "url": "https://demo.example.com/bosch-hiring-engineers-8",
        "company": "Bosch",
        "country": "Almanya",
        "city": "Stuttgart",
        "industry": "otomotiv",
        "signal_type": SignalType.HIRING_WAVE,
        "summary_tr": "Bosch, elektrikli araç bileşenleri bölümü için 3.000 mühendis işe alacağını açıkladı. İşe alımlar 2025 boyunca gerçekleştirilecek.",
        "confidence": 0.83,
        "impact": 0.75,
        "evidence": ["Bosch announces hiring of 3,000 engineers", "Recruitment for EV component division throughout 2025"],
    },
    {
        "article_title": "TotalEnergies to Build 5 GW Solar Farm in Morocco",
        "url": "https://demo.example.com/totalenergies-morocco-solar-9",
        "company": "TotalEnergies",
        "country": "Fas",
        "city": "Ouarzazate",
        "industry": "enerji",
        "signal_type": SignalType.ENERGY_PROJECT,
        "summary_tr": "TotalEnergies, Fas'ın Ouarzazate bölgesinde 5 GW kapasiteli güneş enerjisi çiftliği kuracağını açıkladı. Proje 2027'de tamamlanacak ve Avrupa'ya enerji ihraç edilecek.",
        "confidence": 0.86,
        "impact": 0.84,
        "evidence": ["TotalEnergies to build 5 GW solar farm in Morocco", "Project will export energy to Europe from 2027"],
    },
    {
        "article_title": "TSMC Partners with Sony for Advanced Packaging in Japan",
        "url": "https://demo.example.com/tsmc-sony-partnership-10",
        "company": "TSMC",
        "country": "Japonya",
        "city": "Kumamoto",
        "industry": "yari_iletken",
        "signal_type": SignalType.PARTNERSHIP,
        "summary_tr": "TSMC ve Sony, Japonya'nın Kumamoto şehrinde gelişmiş çip paketleme teknolojisi için stratejik ortaklık anlaşması imzaladı. Ortaklık 2 milyar dolar yatırım içeriyor.",
        "confidence": 0.88,
        "impact": 0.87,
        "evidence": ["TSMC and Sony sign strategic partnership for advanced packaging", "$2 billion investment in Kumamoto facility"],
    },
]

DEMO_TRENDS = [
    {
        "label": "Yarı İletken sektöründe yoğunlaşma",
        "description_tr": "Son 14 günde yarı iletken sektöründe 8 sinyal tespit edildi. Öne çıkan coğrafyalar: ABD, Japonya, Güney Kore. Bu yoğunlaşma, sektörde güçlü bir yatırım momentumu işaret etmektedir.",
        "sector": "yari_iletken",
        "geography": None,
        "score": 0.87,
        "count": 8,
    },
    {
        "label": "Avrupa'da veri merkezi yatırım ivmesi",
        "description_tr": "Avrupa'da son 14 günde 6 veri merkezi sinyali kaydedildi. Aktif ülkeler: Polonya, Hollanda, İsveç, Macaristan. Ülke, bu dönemde güçlü bir yatırım aktivitesi sergiliyor.",
        "sector": "veri_merkezi",
        "geography": "Avrupa",
        "score": 0.82,
        "count": 6,
    },
    {
        "label": "Gelişen örüntü: Yeni Tesis yatırımları",
        "description_tr": "Son 14 günde 'new_facility' kategorisinde 12 sinyal tespit edildi. Coğrafi dağılım: ABD, Macaristan, Polonya, Türkiye. Bu örüntü, ilgili alanda yapısal bir momentum işaret etmektedir.",
        "sector": None,
        "geography": None,
        "score": 0.79,
        "count": 12,
    },
    {
        "label": "Türkiye'de yatırım ivmesi",
        "description_tr": "Türkiye'de son 14 günde 5 stratejik sinyal kaydedildi. Aktif sektörler: otomotiv, enerji, yari_iletken. Ülke, bu dönemde güçlü bir yatırım aktivitesi sergiliyor.",
        "sector": "otomotiv",
        "geography": "Türkiye",
        "score": 0.75,
        "count": 5,
    },
]


def create_demo_data():
    """Demo veri oluştur."""
    init_db()
    db = SessionLocal()

    # Demo kaynak oluştur
    demo_source = db.query(Source).filter(
        Source.base_url == "https://demo.example.com"
    ).first()

    if not demo_source:
        demo_source = Source(
            name="Demo Kaynak",
            base_url="https://demo.example.com",
            source_type="news_site",
            country="Global",
            language="en",
            trust_score=0.85,
            priority_score=0.80,
            is_active=False,
            notes="Demo amaçlı test kaynağı",
        )
        db.add(demo_source)
        db.commit()
        db.refresh(demo_source)

    # Demo makaleler ve sinyaller oluştur
    signal_count = 0
    for i, signal_data in enumerate(DEMO_SIGNALS):
        # Makale var mı?
        existing_article = db.query(Article).filter(
            Article.url == signal_data["url"]
        ).first()

        if not existing_article:
            article = Article(
                source_id=demo_source.id,
                title=signal_data["article_title"],
                url=signal_data["url"],
                published_at=datetime.utcnow() - timedelta(hours=random.randint(1, 72)),
                cleaned_text=signal_data["summary_tr"],
                is_processed=True,
                fetched_at=datetime.utcnow(),
            )
            db.add(article)
            db.flush()

            composite = signal_data["confidence"] * 0.45 + signal_data["impact"] * 0.40 + 0.85 * 0.15

            signal = Signal(
                article_id=article.id,
                detected_company=signal_data.get("company"),
                industry=signal_data["industry"],
                country=signal_data.get("country"),
                city_or_region=signal_data.get("city"),
                signal_type=signal_data["signal_type"],
                signal_type_label_tr=_type_label(signal_data["signal_type"]),
                summary_tr=signal_data["summary_tr"],
                confidence_score=signal_data["confidence"],
                impact_score=signal_data["impact"],
                relevance_score=(signal_data["confidence"] + signal_data["impact"]) / 2,
                composite_score=round(composite, 3),
                evidence_phrases=signal_data.get("evidence", []),
                keywords_matched=["demo"],
                relevant_sectors=[signal_data["industry"]],
                review_status=ReviewStatus.APPROVED,
                detection_method="demo",
                created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 120)),
            )
            db.add(signal)
            signal_count += 1

    # Demo trendler
    trend_count = 0
    for trend_data in DEMO_TRENDS:
        existing = db.query(TrendCluster).filter(
            TrendCluster.label == trend_data["label"]
        ).first()
        if not existing:
            trend = TrendCluster(
                label=trend_data["label"],
                description_tr=trend_data["description_tr"],
                sector=trend_data["sector"],
                geography=trend_data["geography"],
                cluster_score=trend_data["score"],
                signal_count=trend_data["count"],
                is_active=True,
                first_seen_at=datetime.utcnow() - timedelta(days=10),
                last_seen_at=datetime.utcnow() - timedelta(hours=6),
            )
            db.add(trend)
            trend_count += 1

    db.commit()
    db.close()

    print(f"✓ Demo veri oluşturuldu: {signal_count} sinyal, {trend_count} trend")


def _type_label(signal_type):
    from backend.signals.keywords import SIGNAL_TYPE_LABELS_TR
    return SIGNAL_TYPE_LABELS_TR.get(signal_type, "")


if __name__ == "__main__":
    create_demo_data()
