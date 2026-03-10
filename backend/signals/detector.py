"""
Rules-based sinyal tespit motoru.
Ollama olmadan da tam fonksiyonlu çalışır.
"""
import re
import logging
from typing import Optional, List, Dict, Tuple
from datetime import datetime

from backend.db.models import Article, Signal, SignalType, ReviewStatus, Industry
from backend.signals.keywords import (
    SIGNAL_PATTERNS,
    NEGATIVE_PATTERNS,
    SECTOR_KEYWORDS,
    SIGNAL_TYPE_LABELS_TR,
    COUNTRY_NORMALIZE,
)

logger = logging.getLogger(__name__)

# Ülke adı tanıma için regex pattern'leri
COUNTRY_PATTERNS = [
    r'\b(Turkey|Türkiye|Turkey\'s)\b',
    r'\b(Germany|Deutschland|Germany\'s)\b',
    r'\b(United States|USA|U\.S\.A\.|U\.S\.)\b',
    r'\b(China|PRC|China\'s)\b',
    r'\b(Japan|Japan\'s)\b',
    r'\b(South Korea|Korea)\b',
    r'\b(India|India\'s)\b',
    r'\b(Poland|Poland\'s)\b',
    r'\b(France|France\'s)\b',
    r'\b(United Kingdom|UK|Britain)\b',
    r'\b(Saudi Arabia|KSA)\b',
    r'\b(UAE|United Arab Emirates)\b',
    r'\b(Morocco|Fas)\b',
    r'\b(Mexico|México)\b',
    r'\b(Brazil|Brasil)\b',
    r'\b(Canada)\b',
    r'\b(Australia)\b',
    r'\b(Netherlands|Holland)\b',
    r'\b(Spain|España|İspanya)\b',
    r'\b(Italy|Italia|İtalya)\b',
    r'\b(Hungary|Macaristan)\b',
]

# Para birimi ve büyüklük pattern'leri - yatırım büyüklüğü tahmini için
INVESTMENT_AMOUNT_PATTERN = re.compile(
    r'(\$|€|£|¥|₺|USD|EUR|GBP|TL|TRY)\s*'
    r'(\d+(?:\.\d+)?)\s*'
    r'(billion|million|trillion|milyar|milyon|trilyon)',
    re.IGNORECASE
)

# Şirket adı için basit heuristic
COMPANY_SUFFIXES = [
    r'\b\w+\s+(Inc\.|Corp\.|Ltd\.|LLC|GmbH|A\.Ş\.|A\.S\.|SA|PLC|SE|NV|BV)\b',
    r'\b\w+\s+(?:Group|Holdings|Industries|Manufacturing|Technologies|Energy)\b',
]


class RulesBasedDetector:
    """
    Makale metninden sinyal tespit eden kural motoru.
    Her makale için 0 veya daha fazla Signal üretir.
    """

    def __init__(self, source_trust_score: float = 0.5):
        self.source_trust_score = source_trust_score

    def analyze(self, article: Article) -> List[Dict]:
        """
        Makaleyi analiz et ve bulunan sinyalleri dict listesi olarak döndür.
        Veritabanı işlemleri bu fonksiyonda yapılmaz.
        """
        text = self._get_text(article)
        if not text or len(text) < 100:
            return []

        text_lower = text.lower()
        results = []

        for signal_type, (patterns, base_score) in SIGNAL_PATTERNS.items():
            matched_patterns = []
            for pattern in patterns:
                if pattern.lower() in text_lower:
                    matched_patterns.append(pattern)

            if not matched_patterns:
                continue

            # Negatif filtre uygula
            negative_adjustment = 0.0
            for neg_pattern, penalty in NEGATIVE_PATTERNS:
                if neg_pattern.lower() in text_lower:
                    negative_adjustment += penalty

            # Eşleşen pattern sayısına göre bonus
            match_bonus = min(0.15, (len(matched_patterns) - 1) * 0.05)

            # Kaynak güven skoru etkisi
            trust_adjustment = (self.source_trust_score - 0.5) * 0.2

            confidence = base_score + match_bonus + negative_adjustment + trust_adjustment
            confidence = max(0.0, min(1.0, confidence))

            if confidence < 0.25:
                continue

            # Sektör tespiti
            industry = self._detect_industry(text_lower, signal_type)

            # Ülke tespiti
            country = self._detect_country(text)

            # Şirket tespiti
            company = self._detect_company(text)

            # Şehir / bölge tespiti
            location = self._detect_location(text, country)

            # Kanıt cümleleri
            evidence = self._extract_evidence(text, matched_patterns)

            # Etki skoru
            impact = self._calculate_impact(
                text_lower, signal_type, confidence,
                industry, country
            )

            # Bileşik skor
            composite = self._composite_score(confidence, impact, self.source_trust_score)

            # İlgili sektörler
            relevant_sectors = self._get_relevant_sectors(text_lower)

            # Review durumu
            review_status = self._determine_review_status(confidence, impact)

            results.append({
                "signal_type": signal_type,
                "signal_type_label_tr": SIGNAL_TYPE_LABELS_TR.get(signal_type, ""),
                "detected_company": company,
                "industry": industry,
                "country": country,
                "city_or_region": location,
                "confidence_score": round(confidence, 3),
                "impact_score": round(impact, 3),
                "relevance_score": round(confidence * 0.6 + impact * 0.4, 3),
                "composite_score": round(composite, 3),
                "evidence_phrases": evidence[:5],  # Max 5 kanıt
                "keywords_matched": matched_patterns[:8],
                "relevant_sectors": relevant_sectors,
                "summary_tr": self._generate_summary_tr(
                    article.title, signal_type, company, country, industry
                ),
                "review_status": review_status,
                "detection_method": "rules",
            })

        # Aynı makaleden en yüksek skorlu 3 sinyali al
        results.sort(key=lambda x: x["composite_score"], reverse=True)
        return results[:3]

    def _get_text(self, article: Article) -> str:
        """Analiz için en iyi metni seç."""
        parts = []
        if article.title:
            parts.append(article.title)
            parts.append(article.title)  # Başlık ağırlıklı
        if article.cleaned_text:
            parts.append(article.cleaned_text[:3000])
        elif article.raw_text:
            parts.append(article.raw_text[:3000])
        return " ".join(parts)

    def _detect_industry(
        self, text_lower: str, signal_type: SignalType
    ) -> Optional[str]:
        """Metinden birincil sektörü tespit et."""
        # Sinyal tipine göre default sektör haritası
        type_to_industry = {
            SignalType.DATA_CENTER: Industry.DATA_CENTER,
            SignalType.SEMICONDUCTOR: Industry.SEMICONDUCTOR,
            SignalType.AUTOMOTIVE: Industry.AUTOMOTIVE,
            SignalType.ENERGY_PROJECT: Industry.ENERGY,
            SignalType.MINING: Industry.MINING,
            SignalType.DEFENSE: Industry.DEFENSE,
            SignalType.LOGISTICS: Industry.LOGISTICS,
        }

        if signal_type in type_to_industry:
            return type_to_industry[signal_type].value

        # Keyword eşleştirme
        sector_scores: Dict[str, int] = {}
        for industry, keywords in SECTOR_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                industry_val = industry.value if hasattr(industry, 'value') else str(industry)
                sector_scores[industry_val] = score

        if sector_scores:
            return max(sector_scores, key=sector_scores.get)

        return Industry.MANUFACTURING.value  # Default

    def _detect_country(self, text: str) -> Optional[str]:
        """Metinden ülke adını tespit et."""
        for pattern in COUNTRY_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                country_raw = match.group(0).lower().strip("'s").strip()
                # Normalizasyon
                return COUNTRY_NORMALIZE.get(country_raw, match.group(0).strip("'s"))
        return None

    def _detect_company(self, text: str) -> Optional[str]:
        """Metinden şirket adını tespit et."""
        for pattern in COMPANY_SUFFIXES:
            match = re.search(pattern, text)
            if match:
                company = match.group(0).strip()
                if len(company) > 3 and len(company) < 100:
                    return company
        return None

    def _detect_location(
        self, text: str, country: Optional[str]
    ) -> Optional[str]:
        """Şehir veya bölge tespiti."""
        # Basit heuristic: Büyük harfle başlayan ve bilinen şehirlere benzeyen kelimeleri ara
        common_cities = [
            "İstanbul", "Istanbul", "Ankara", "İzmir", "Izmir", "Bursa",
            "Kocaeli", "Gebze", "Berlin", "Munich", "Hamburg", "Frankfurt",
            "Paris", "Lyon", "London", "Manchester", "New York", "Detroit",
            "Shanghai", "Beijing", "Guangzhou", "Tokyo", "Seoul", "Busan",
            "Warsaw", "Kraków", "Prague", "Budapest", "Bucharest",
            "Casablanca", "Cairo", "Dubai", "Riyadh", "Toronto",
            "Mexico City", "São Paulo",
        ]
        text_lower_orig = text.lower()
        for city in common_cities:
            if city.lower() in text_lower_orig:
                return city
        return None

    def _extract_evidence(
        self, text: str, matched_patterns: List[str]
    ) -> List[str]:
        """Kanıt cümlelerini çıkar."""
        sentences = re.split(r'[.!?\n]', text)
        evidence = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 30 or len(sentence) > 500:
                continue
            sentence_lower = sentence.lower()
            for pattern in matched_patterns:
                if pattern.lower() in sentence_lower:
                    evidence.append(sentence)
                    break
        return evidence[:5]

    def _calculate_impact(
        self,
        text_lower: str,
        signal_type: SignalType,
        confidence: float,
        industry: Optional[str],
        country: Optional[str],
    ) -> float:
        """Sinyalin potansiyel etkisini hesapla."""
        impact = confidence * 0.6  # Temel: güven skorunun %60'ı

        # Yatırım büyüklüğü bonus
        amount_match = INVESTMENT_AMOUNT_PATTERN.search(text_lower)
        if amount_match:
            magnitude = amount_match.group(3).lower()
            if "billion" in magnitude or "milyar" in magnitude:
                impact += 0.20
            elif "million" in magnitude or "milyon" in magnitude:
                impact += 0.10

        # Yüksek etkili sinyal tipi bonusları
        high_impact_types = {
            SignalType.NEW_FACILITY: 0.15,
            SignalType.SEMICONDUCTOR: 0.20,
            SignalType.DATA_CENTER: 0.15,
            SignalType.ENERGY_PROJECT: 0.15,
            SignalType.ACQUISITION: 0.12,
            SignalType.DEFENSE: 0.10,
        }
        if signal_type in high_impact_types:
            impact += high_impact_types[signal_type]

        # Stratejik ülkeler
        strategic_countries = ["Türkiye", "Almanya", "ABD", "Çin", "Japonya", "Güney Kore"]
        if country and any(sc in country for sc in strategic_countries):
            impact += 0.08

        # Anahtar büyüklük kelimeleri
        if any(kw in text_lower for kw in ["gigawatt", "gigafactory", "megafactory"]):
            impact += 0.15

        return max(0.0, min(1.0, impact))

    def _composite_score(
        self, confidence: float, impact: float, trust: float
    ) -> float:
        """Nihai bileşik skor."""
        return (confidence * 0.45) + (impact * 0.40) + (trust * 0.15)

    def _get_relevant_sectors(self, text_lower: str) -> List[str]:
        """İlgili sektörlerin listesini döndür."""
        sectors = []
        for industry, keywords in SECTOR_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            if matches >= 2:
                industry_val = industry.value if hasattr(industry, 'value') else str(industry)
                sectors.append(industry_val)
        return sectors[:5]

    def _determine_review_status(
        self, confidence: float, impact: float
    ) -> ReviewStatus:
        """Güven ve etki skoruna göre review durumunu belirle."""
        if confidence >= 0.70 and impact >= 0.60:
            return ReviewStatus.APPROVED
        elif confidence < 0.40 or (confidence < 0.55 and impact < 0.45):
            return ReviewStatus.NEEDS_REVIEW
        return ReviewStatus.PENDING

    def _generate_summary_tr(
        self,
        title: Optional[str],
        signal_type: SignalType,
        company: Optional[str],
        country: Optional[str],
        industry: Optional[str],
    ) -> str:
        """Basit kural tabanlı Türkçe özet üret."""
        signal_label = SIGNAL_TYPE_LABELS_TR.get(signal_type, "Sinyal")
        parts = []

        if company:
            parts.append(company)
        if country:
            parts.append(f"({country})")

        action_map = {
            SignalType.NEW_FACILITY: "yeni tesis yatırımı tespit edildi",
            SignalType.EXPANSION: "kapasite artışı sinyali alındı",
            SignalType.INVESTMENT: "yatırım kararı açıklandı",
            SignalType.INCENTIVE: "yatırım teşviği haberi",
            SignalType.HIRING_WAVE: "büyük çaplı işe alım sinyali",
            SignalType.INFRASTRUCTURE: "altyapı projesi başlatıldı",
            SignalType.ENERGY_PROJECT: "enerji projesi duyuruldu",
            SignalType.PATENT: "patent / teknoloji gelişmesi",
            SignalType.PARTNERSHIP: "stratejik ortaklık kuruldu",
            SignalType.ACQUISITION: "satın alma / birleşme hareketi",
            SignalType.SUPPLY_CHAIN: "tedarik zinciri genişlemesi",
            SignalType.DATA_CENTER: "veri merkezi yatırımı",
            SignalType.MINING: "madencilik projesi genişliyor",
            SignalType.SEMICONDUCTOR: "yarı iletken üretim yatırımı",
            SignalType.AUTOMOTIVE: "otomotiv üretim yatırımı",
            SignalType.DEFENSE: "savunma sanayi gelişmesi",
            SignalType.LOGISTICS: "lojistik altyapı genişlemesi",
        }

        action = action_map.get(signal_type, "stratejik gelişme")
        parts.append(action)

        if title and len(title) < 200:
            summary = " ".join(parts) + f". Kaynak başlığı: {title}"
        else:
            summary = " ".join(parts)

        return summary[:500]
