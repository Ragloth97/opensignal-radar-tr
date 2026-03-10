"""
TRENG Mühendislik & İRDA Yapı — özel sinyal skorlama motoru.

Her sinyal için 0-100 arası iki ayrı skor üretir:
- treng_score: Toz/filtrasyon/boyahane/konveyör projesi ihtimali
- irda_score : EPC/taahhüt/büyük altyapı/enerji projesi ihtimali
"""
import re
from typing import Tuple

# ─── TRENG Anahtar Kelimeleri ─────────────────────────────────────────────────
# (keyword, puan) — maksimum 100'e normalize edilecek

TRENG_KEYWORDS: list[Tuple[str, int]] = [
    # Toz & talaş toplama
    ("toz toplama", 25), ("dust collection", 25), ("dust collector", 25),
    ("talaş toplama", 22), ("chip collection", 20), ("talaş", 15),
    ("döküm tozu", 18), ("metal tozu", 18),

    # Filtrasyon
    ("filtrasyon", 22), ("filtration", 22),
    ("kartuş filtre", 24), ("cartridge filter", 24),
    ("torba filtre", 22), ("bag filter", 22), ("baghouse", 22),
    ("jet-pulse", 24), ("jet pulse", 24), ("pulse jet", 22),
    ("baca filtresi", 22), ("stack filter", 20),
    ("hava filtresi", 15), ("air filtration", 15),
    ("hepa filtre", 18), ("hepa filter", 18),

    # Boyahane & Kaplama
    ("boyahane", 28), ("paint shop", 28), ("paint booth", 28),
    ("sprey kabini", 25), ("spray booth", 25),
    ("boya tesisi", 26), ("painting facility", 24),
    ("kaplama", 18), ("coating", 16), ("surface treatment", 16),
    ("toz boya", 20), ("powder coating", 20),
    ("elektrostatik boya", 22), ("electrostatic paint", 20),
    ("e-coat", 18), ("elektroforez", 18),
    ("ön işlem", 14), ("pretreatment", 14),
    ("emisyon kontrolü", 18), ("emission control", 18),

    # Kaynak dumanı
    ("kaynak dumanı", 25), ("welding fume", 25),
    ("fume extraction", 22), ("duman emiş", 22),
    ("kaynak havalandırma", 22), ("welding ventilation", 20),
    ("kaynak kabini", 20),

    # Konveyör
    ("konveyör", 20), ("conveyor", 20),
    ("bantlı konveyör", 22), ("belt conveyor", 22),
    ("zincirli konveyör", 22), ("chain conveyor", 22),
    ("pnömatik konveyör", 22), ("pneumatic conveyor", 22),
    ("vida konveyör", 20), ("screw conveyor", 20),
    ("konveyör sistemi", 22), ("conveyor system", 22),

    # Havalandırma & Fan
    ("endüstriyel havalandırma", 18), ("industrial ventilation", 18),
    ("proses havalandırma", 20), ("process ventilation", 20),
    ("mekanik havalandırma", 16), ("mechanical ventilation", 16),
    ("endüstriyel fan", 18), ("industrial fan", 18),
    ("aksiyel fan", 16), ("radyal fan", 16), ("centrifugal fan", 16),
    ("kanallama", 15), ("ducting", 15), ("duct system", 15),
    ("hava kanalı", 14), ("air duct", 14),

    # Proses & Ekipman genel
    ("mekanik proses", 16), ("mechanical process", 14),
    ("endüstriyel aspirasyon", 18),
    ("baca sistemi", 16), ("exhaust system", 14),
    ("davlumbaz", 14), ("hood", 10),

    # Tesis yatırımları — TRENG için potansiyel müşteri
    ("üretim hattı", 18), ("production line", 18),
    ("yeni üretim hattı", 22), ("new production line", 22),
    ("üretim kapasitesi", 16), ("production capacity", 14),
    ("yeni fabrika", 16), ("new factory", 14), ("new plant", 14),
    ("tesis genişlemesi", 16), ("facility expansion", 14),
    ("kapasite artışı", 14), ("capacity expansion", 12),
    ("modernizasyon", 12), ("modernization", 10),
    ("endüstriyel modernizasyon", 16),
    ("ahşap işleme", 18), ("wood processing", 18),  # Talaş/toz yoğun
    ("mobilya üretimi", 16), ("furniture manufacturing", 16),
    ("döküm", 16), ("casting", 14), ("foundry", 16),
    ("metal işleme", 16), ("metalworking", 16),
    ("tekstil", 10), ("textile", 10),
    ("plastik enjeksiyon", 14), ("plastic injection", 14),
    ("otomotiv yan sanayi", 18), ("auto parts", 14),
    ("gıda üretim", 12), ("food production", 10),

    # Lokasyon bonus
    ("türkiye", 8), ("turkey", 8), ("osb", 10),
    ("organize sanayi", 10), ("organized industrial", 10),
]

# ─── İRDA Anahtar Kelimeleri ──────────────────────────────────────────────────

IRDA_KEYWORDS: list[Tuple[str, int]] = [
    # ÇED & İhale
    ("çed", 28), ("ÇED", 28), ("çevresel etki", 25),
    ("environmental impact assessment", 25), ("eia", 22),
    ("ihale", 25), ("tender", 22), ("ihale açıldı", 28),
    ("ihale duyurusu", 28), ("kamu ihalesi", 28),
    ("yap-işlet-devret", 22), ("BOT", 20), ("PPP", 20),
    ("yap-işlet", 18), ("build operate", 18),

    # EPC & Taahhüt
    ("EPC", 28), ("epc sözleşmesi", 30), ("epc müteahhit", 28),
    ("epc kontratı", 28), ("EPC contract", 28),
    ("ana yüklenici", 25), ("main contractor", 25), ("general contractor", 22),
    ("taahhüt", 20), ("müteahhit", 22), ("inşaat taahhüt", 24),
    ("mekanik taahhüt", 25), ("mechanical contract", 22),
    ("anahtar teslim", 22), ("turnkey", 22),

    # Enerji Santralleri
    ("enerji santrali", 25), ("power plant", 22), ("elektrik santrali", 25),
    ("termik santral", 25), ("thermal power", 22),
    ("hidroelektrik", 22), ("hydroelectric", 22), ("baraj", 20),
    ("jeotermal", 22), ("geothermal", 20),
    ("rüzgar santrali", 22), ("wind power plant", 20),
    ("güneş santrali", 18), ("solar power plant", 18),
    ("nükleer santral", 25), ("nuclear power", 22),
    ("enerji depolama", 18), ("energy storage", 16),
    ("doğalgaz santrali", 25), ("gas power plant", 22),
    ("kombine çevrim", 22), ("combined cycle", 20),

    # Petrol & Gaz & Kimya
    ("rafineri", 28), ("refinery", 26),
    ("petrokimya", 28), ("petrochemical", 26),
    ("petrol", 18), ("oil", 12), ("petroleum", 18),
    ("doğalgaz", 20), ("natural gas", 16), ("lng", 22),
    ("boru hattı", 22), ("pipeline", 20),
    ("depolama tankı", 20), ("storage tank", 18),
    ("kimya tesisi", 22), ("chemical plant", 20),
    ("gübre fabrikası", 22), ("fertilizer plant", 20),

    # Havaalanı & Liman
    ("havaalanı", 24), ("airport", 22), ("havalimanı", 24),
    ("pist", 18), ("terminal binası", 20),
    ("liman", 24), ("port", 20), ("liman inşaatı", 26),
    ("tersane", 22), ("shipyard", 20),
    ("derin deniz limanı", 26), ("container terminal", 22),

    # Büyük Altyapı
    ("altyapı", 16), ("infrastructure", 14),
    ("köprü", 18), ("bridge", 16), ("tünel", 20), ("tunnel", 18),
    ("demiryolu", 22), ("railway", 20), ("metro", 20),
    ("otoyol", 18), ("highway", 16),
    ("sanayi bölgesi", 18), ("industrial zone", 16),
    ("organize sanayi bölgesi", 20), ("osb altyapı", 22),

    # Çelik & Yapı
    ("çelik konstrüksiyon", 24), ("steel construction", 22),
    ("steel structure", 22), ("çelik yapı", 22),
    ("prefabrik", 20), ("prefabricated", 18),
    ("kenet çatı", 22), ("standing seam", 20), ("kenet", 18),
    ("metal çatı", 18), ("metal roof", 16),
    ("sandviç panel", 16), ("sandwich panel", 16),
    ("endüstriyel yapı", 18), ("industrial building", 16),
    ("fabrika inşaatı", 24), ("factory construction", 22),
    ("depo inşaatı", 18), ("warehouse construction", 16),

    # Büyük Yatırım Sinyalleri
    ("büyük yatırım", 16), ("major investment", 14),
    ("milyar", 16), ("billion", 14),
    ("yatırım teşvik belgesi", 20), ("incentive certificate", 18),
    ("turizm tesisi", 14), ("hastane", 14), ("hospital", 14),
    ("üniversite", 12), ("campus", 12),
    ("veri merkezi inşaatı", 22), ("data center construction", 20),

    # Lokasyon & Sektör bonus
    ("türkiye", 8), ("turkey", 8),
    ("endüstriyel tesis", 18), ("industrial facility", 16),
    ("sanayi tesisi", 18), ("industrial plant", 16),
]

# Ön-derle: küçük harfe çevir
_TRENG_KW = [(kw.lower(), score) for kw, score in TRENG_KEYWORDS]
_IRDA_KW = [(kw.lower(), score) for kw, score in IRDA_KEYWORDS]

# Maksimum teorik toplam (normalize için)
_TRENG_MAX = 120   # Pratik üst sınır
_IRDA_MAX = 120


def score_signal(text: str, title: str = "") -> Tuple[float, float]:
    """
    Ham makale metni ve başlıktan TRENG ve İRDA skorlarını hesapla.
    Returns: (treng_score, irda_score) — her biri 0.0 – 100.0
    """
    combined = (title + " " + title + " " + text).lower()  # Başlık 2x ağırlık

    treng_raw = 0
    irda_raw = 0

    for kw, pts in _TRENG_KW:
        if kw in combined:
            # Kaç kez geçiyor? (max 3x sayılır)
            count = min(combined.count(kw), 3)
            treng_raw += pts * (1 + (count - 1) * 0.3)

    for kw, pts in _IRDA_KW:
        if kw in combined:
            count = min(combined.count(kw), 3)
            irda_raw += pts * (1 + (count - 1) * 0.3)

    treng_score = min(100.0, (treng_raw / _TRENG_MAX) * 100)
    irda_score = min(100.0, (irda_raw / _IRDA_MAX) * 100)

    return round(treng_score, 1), round(irda_score, 1)


def match_watchlist(text: str, title: str, companies: list) -> list:
    """
    Takip listesindeki şirket adlarını metin içinde ara.
    Returns: Eşleşen şirketlerin [{"id", "name", "priority", "owner_company"}] listesi
    """
    combined = (title + " " + text).lower()
    matched = []

    for company in companies:
        names_to_check = [company.name]
        if company.aliases:
            names_to_check.extend(company.aliases)

        for name in names_to_check:
            if not name:
                continue
            # Kısaltmalar için word boundary
            pattern = r'\b' + re.escape(name.lower()) + r'\b'
            if re.search(pattern, combined, re.IGNORECASE):
                matched.append({
                    "id": company.id,
                    "name": company.name,
                    "priority": company.priority,
                    "owner_company": company.owner_company,
                })
                break  # Aynı şirketi birden fazla alias ile sayma

    return matched
