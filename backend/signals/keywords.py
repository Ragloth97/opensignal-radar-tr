"""
Sinyal tespit için keyword sözlükleri ve kural tanımları.
Bu modül rules-based motorun kalbidir.
"""
from typing import Dict, List, Tuple
from backend.db.models import SignalType, Industry


# ─── Pozitif Sinyal Pattern'leri ─────────────────────────────────────────────
# Her sinyal tipi için (pattern_listesi, base_score) çifti

SIGNAL_PATTERNS: Dict[SignalType, Tuple[List[str], float]] = {

    SignalType.NEW_FACILITY: (
        [
            "new plant", "new facility", "new factory", "new manufacturing",
            "greenfield", "new production facility", "yeni fabrika",
            "yeni tesis", "yeni üretim tesisi", "new site", "new campus",
            "new production plant", "built a new", "opening a plant",
            "factory construction", "plant construction", "tesis kurulumu",
            "fabrika yatırımı", "new manufacturing hub", "production hub",
            "yeni üretim merkezi", "new industrial complex",
        ],
        0.85
    ),

    SignalType.EXPANSION: (
        [
            "capacity expansion", "capacity increase", "expanding production",
            "expansion plan", "expanded operations", "kapasite artışı",
            "kapasite genişlemesi", "üretim artışı", "expanding capacity",
            "doubling capacity", "tripling production", "scale up",
            "scaling up production", "production ramp", "ramp-up",
            "additional production line", "new production line",
            "yeni üretim hattı", "hattını artırıyor", "kapasitesini artırıyor",
            "genişleme planı", "büyüme planı", "expansion phase",
        ],
        0.80
    ),

    SignalType.INVESTMENT: (
        [
            "invests $", "invests €", "investment of", "capital investment",
            "billion investment", "million investment", "yatırım yapıyor",
            "yatırım kararı", "yatırım planı", "major investment",
            "significant investment", "commits to invest", "pledges investment",
            "investing in", "new investment round", "capital commitment",
            "milyar yatırım", "milyon yatırım", "yatırım tutarı",
            "financial commitment", "funding round closed",
        ],
        0.75
    ),

    SignalType.INCENTIVE: (
        [
            "investment incentive", "tax incentive", "government grant",
            "subsidy", "state aid", "incentive certificate", "teşvik belgesi",
            "yatırım teşviği", "devlet desteği", "sübvansiyon",
            "teşvik kapsamında", "government support", "eu funding",
            "state subsidy", "tax break", "tax holiday", "vergi indirimi",
            "free zone", "serbest bölge", "organized industrial zone",
            "osb yatırımı", "grant received", "funding secured",
        ],
        0.78
    ),

    SignalType.HIRING_WAVE: (
        [
            "hiring hundreds", "hiring thousands", "mass recruitment",
            "thousands of jobs", "new jobs", "workforce expansion",
            "toplu işe alım", "büyük istihdam", "yeni istihdam",
            "thousands of employees", "jobs created", "creating jobs",
            "iş imkânı", "çalışan alımı", "işe alım dalgası",
            "recruitment drive", "talent acquisition",
            "seeking to hire", "announces hiring", "job creation",
        ],
        0.72
    ),

    SignalType.INFRASTRUCTURE: (
        [
            "infrastructure project", "construction started",
            "infrastructure investment", "infrastructure development",
            "altyapı projesi", "altyapı yatırımı", "inşaat başladı",
            "construction begins", "breaking ground", "groundbreaking ceremony",
            "temel atma töreni", "ihracat altyapısı", "logistics infrastructure",
            "port expansion", "liman genişlemesi", "rail connection",
            "road construction", "bridge construction",
        ],
        0.70
    ),

    SignalType.ENERGY_PROJECT: (
        [
            "power plant", "energy project", "renewable energy",
            "solar farm", "wind farm", "battery storage",
            "enerji projesi", "enerji yatırımı", "güneş enerjisi",
            "rüzgar enerjisi", "nükleer santral", "hidroelektrik",
            "energy storage", "grid project", "power grid",
            "elektrik santrali", "enerji depolama", "green energy",
            "hydrogen project", "lng terminal", "natural gas",
            "offshore wind", "photovoltaic",
        ],
        0.80
    ),

    SignalType.PATENT: (
        [
            "patent filed", "patent granted", "new patent",
            "intellectual property", "technology patent",
            "patent başvurusu", "patent tescili", "buluş patenti",
            "proprietary technology", "licensing agreement",
            "technology transfer", "r&d breakthrough",
            "araştırma geliştirme", "ar-ge patent",
        ],
        0.65
    ),

    SignalType.PARTNERSHIP: (
        [
            "strategic partnership", "joint venture", "collaboration agreement",
            "strategic alliance", "memorandum of understanding",
            "stratejik ortaklık", "iş birliği anlaşması", "ortak girişim",
            "mou signed", "agreement signed", "partnership signed",
            "anlaşma imzalandı", "mutabakat muhtırası",
            "technology agreement", "supply agreement",
            "tedarik anlaşması", "çerçeve anlaşması",
        ],
        0.70
    ),

    SignalType.ACQUISITION: (
        [
            "acquisition", "merger", "acquires", "takeover",
            "buyout", "satın alma", "birleşme", "devralma",
            "merge with", "acquire stake", "majority stake",
            "controlling stake", "asset purchase", "company acquisition",
            "firma satın aldı", "şirket devraldı",
        ],
        0.75
    ),

    SignalType.SUPPLY_CHAIN: (
        [
            "supply chain", "tedarik zinciri", "local sourcing",
            "domestic supplier", "nearshoring", "reshoring",
            "tedarikçi geliştirme", "yerli tedarik", "local manufacturing",
            "supplier development", "procurement strategy",
            "component supply", "raw material",
            "hammadde tedariki", "lojistik merkezi",
        ],
        0.68
    ),

    SignalType.DATA_CENTER: (
        [
            "data center", "datacenter", "veri merkezi",
            "cloud infrastructure", "hyperscale", "server farm",
            "colocation", "edge computing", "cloud region",
            "azure region", "aws region", "google cloud region",
            "bulut altyapısı", "cloud data center", "tier 3", "tier 4",
            "data hall", "megawatt capacity",
        ],
        0.82
    ),

    SignalType.MINING: (
        [
            "mining project", "mining expansion", "ore extraction",
            "mineral processing", "madencilik projesi",
            "maden işletmesi", "maden yatırımı", "lithium mining",
            "cobalt mining", "copper mine", "battery materials",
            "critical minerals", "rare earth", "nadir toprak",
            "pil hammaddesi", "lityum madeni",
        ],
        0.78
    ),

    SignalType.SEMICONDUCTOR: (
        [
            "semiconductor fab", "chip factory", "wafer production",
            "chip manufacturing", "yarı iletken", "çip üretimi",
            "fabless", "foundry", "semiconductor plant",
            "integrated circuit", "transistor", "node process",
            "advanced packaging", "chip packaging",
        ],
        0.85
    ),

    SignalType.AUTOMOTIVE: (
        [
            "ev factory", "electric vehicle plant", "automotive plant",
            "car manufacturing", "otomotiv fabrikası", "elektrikli araç",
            "ev üretimi", "battery pack assembly", "motor production",
            "vehicle assembly", "powertrain", "auto parts",
            "araç üretimi", "otomotiv yatırımı",
        ],
        0.80
    ),

    SignalType.DEFENSE: (
        [
            "defense contract", "military contract", "defense procurement",
            "savunma sanayi", "askeri tedarik", "defense project",
            "weapon system", "drone manufacturing", "insansız hava",
            "zırhlı araç", "savunma projesi", "nato contract",
            "defense investment", "military production",
        ],
        0.80
    ),

    SignalType.LOGISTICS: (
        [
            "logistics hub", "distribution center", "warehouse",
            "lojistik merkezi", "dağıtım merkezi", "depo yatırımı",
            "fulfillment center", "last mile", "freight terminal",
            "intermodal", "cold chain", "lojistik yatırımı",
            "kargo merkezi", "e-commerce logistics",
        ],
        0.70
    ),
}


# ─── Negatif Filtreler ───────────────────────────────────────────────────────
# Bu pattern'lerden herhangi biri bulunursa skor düşer

NEGATIVE_PATTERNS: List[Tuple[str, float]] = [
    # Görüş / fikir yazıları
    ("opinion", -0.25),
    ("commentary", -0.20),
    ("editorial", -0.20),
    ("thought leadership", -0.25),
    ("I believe", -0.15),

    # Muğlak / belirsiz
    ("plans to consider", -0.20),
    ("may invest", -0.15),
    ("could potentially", -0.20),
    ("might expand", -0.15),
    ("rumored", -0.25),
    ("speculated", -0.25),

    # Retrospektif / tarihsel
    ("last year", -0.10),
    ("years ago", -0.10),
    ("historically", -0.15),

    # PR / marka duyuruları
    ("brand partnership", -0.20),
    ("awareness campaign", -0.25),
    ("marketing campaign", -0.25),
    ("award", -0.20),
    ("won the award", -0.25),
    ("recognition", -0.15),

    # Konferans / etkinlik
    ("conference", -0.15),
    ("summit", -0.10),
    ("webinar", -0.20),
    ("event summary", -0.20),

    # İptal / düşüş
    ("cancelled", -0.15),
    ("postponed", -0.15),
    ("delayed", -0.10),
    ("shutdown", -0.10),
    ("layoffs", -0.05),  # Hiring wave ile çakışabilir, hafif düşür
]


# ─── Sektör Sözlüğü ─────────────────────────────────────────────────────────

SECTOR_KEYWORDS: Dict[str, List[str]] = {
    Industry.ENERGY: [
        "energy", "power", "solar", "wind", "nuclear", "hydrogen",
        "battery", "grid", "electric", "enerji", "güneş", "rüzgar",
        "nükleer", "batarya", "elektrik", "lng", "gas",
    ],
    Industry.DATA_CENTER: [
        "data center", "cloud", "server", "datacenter", "hyperscale",
        "colocation", "veri merkezi", "bulut", "sunucu",
    ],
    Industry.SEMICONDUCTOR: [
        "semiconductor", "chip", "wafer", "fab", "transistor",
        "integrated circuit", "yarı iletken", "çip", "elektronik",
    ],
    Industry.AUTOMOTIVE: [
        "automotive", "vehicle", "car", "ev", "electric vehicle",
        "powertrain", "auto", "otomotiv", "araç", "elektrikli araç",
    ],
    Industry.LOGISTICS: [
        "logistics", "supply chain", "freight", "warehouse", "shipping",
        "distribution", "lojistik", "tedarik", "kargo", "depo",
    ],
    Industry.MINING: [
        "mining", "mineral", "ore", "lithium", "cobalt", "copper",
        "madencilik", "maden", "lityum", "kobalt", "bakır",
    ],
    Industry.MANUFACTURING: [
        "manufacturing", "production", "factory", "plant", "industrial",
        "üretim", "fabrika", "sanayi", "imalat",
    ],
    Industry.DEFENSE: [
        "defense", "military", "weapon", "drone", "missile", "naval",
        "savunma", "askeri", "silah", "insansız", "füze",
    ],
    Industry.CONSTRUCTION: [
        "construction", "infrastructure", "building", "real estate",
        "inşaat", "altyapı", "bina", "gayrimenkul",
    ],
    Industry.TECHNOLOGY: [
        "technology", "software", "ai", "artificial intelligence",
        "digital", "tech", "teknoloji", "yazılım", "yapay zeka",
    ],
    Industry.TELECOM: [
        "telecom", "5g", "6g", "network", "fiber", "broadband",
        "telekom", "ağ", "fiber", "geniş bant",
    ],
}


# ─── Türkçe Etiket Haritası ──────────────────────────────────────────────────

SIGNAL_TYPE_LABELS_TR: Dict[SignalType, str] = {
    SignalType.NEW_FACILITY: "Yeni Tesis",
    SignalType.EXPANSION: "Kapasite Artışı",
    SignalType.INVESTMENT: "Yatırım",
    SignalType.INCENTIVE: "Teşvik",
    SignalType.HIRING_WAVE: "İşe Alım Dalgası",
    SignalType.INFRASTRUCTURE: "Altyapı Projesi",
    SignalType.ENERGY_PROJECT: "Enerji Projesi",
    SignalType.PATENT: "Patent / Teknoloji",
    SignalType.PARTNERSHIP: "Stratejik Ortaklık",
    SignalType.ACQUISITION: "Satın Alma / Birleşme",
    SignalType.SUPPLY_CHAIN: "Tedarik Zinciri",
    SignalType.DATA_CENTER: "Veri Merkezi",
    SignalType.MINING: "Madencilik",
    SignalType.SEMICONDUCTOR: "Yarı İletken",
    SignalType.AUTOMOTIVE: "Otomotiv",
    SignalType.DEFENSE: "Savunma",
    SignalType.LOGISTICS: "Lojistik",
    SignalType.IRRELEVANT: "İlgisiz",
}

INDUSTRY_LABELS_TR: Dict[str, str] = {
    "enerji": "Enerji",
    "veri_merkezi": "Veri Merkezi",
    "yari_iletken": "Yarı İletken",
    "otomotiv": "Otomotiv",
    "lojistik": "Lojistik",
    "madencilik": "Madencilik",
    "uretim": "Üretim",
    "savunma": "Savunma",
    "insaat": "İnşaat",
    "finans": "Finans",
    "teknoloji": "Teknoloji",
    "tarim": "Tarım",
    "saglik": "Sağlık",
    "perakende": "Perakende",
    "telekom": "Telekom",
    "diger": "Diğer",
}

# Ülke adı normalizasyon haritası
COUNTRY_NORMALIZE: Dict[str, str] = {
    "turkey": "Türkiye",
    "türkiye": "Türkiye",
    "tr": "Türkiye",
    "usa": "ABD",
    "united states": "ABD",
    "us": "ABD",
    "germany": "Almanya",
    "deutschland": "Almanya",
    "de": "Almanya",
    "china": "Çin",
    "prc": "Çin",
    "uk": "İngiltere",
    "united kingdom": "İngiltere",
    "france": "Fransa",
    "japan": "Japonya",
    "south korea": "Güney Kore",
    "korea": "Güney Kore",
    "india": "Hindistan",
    "poland": "Polonya",
    "hungary": "Macaristan",
    "czech republic": "Çekya",
    "czechia": "Çekya",
    "romania": "Romanya",
    "serbia": "Sırbistan",
    "morocco": "Fas",
    "egypt": "Mısır",
    "saudi arabia": "Suudi Arabistan",
    "uae": "BAE",
    "united arab emirates": "BAE",
    "mexico": "Meksika",
    "brazil": "Brezilya",
    "canada": "Kanada",
    "australia": "Avustralya",
    "netherlands": "Hollanda",
    "spain": "İspanya",
    "italy": "İtalya",
    "sweden": "İsveç",
    "norway": "Norveç",
    "finland": "Finlandiya",
}
