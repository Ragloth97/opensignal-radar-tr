"""
Veritabanı modelleri.
Tüm entity'ler burada tanımlanır.
"""
import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text,
    DateTime, ForeignKey, Enum as SAEnum, JSON, Index
)
from sqlalchemy.orm import relationship
from backend.db.database import Base


# ─── Enum'lar ───────────────────────────────────────────────────────────────

class SourceType(str, enum.Enum):
    RSS = "rss"
    NEWS_SITE = "news_site"
    GOVERNMENT = "government"
    PRESS_ROOM = "press_room"
    CAREER_PAGE = "career_page"
    PATENT = "patent"
    INCENTIVE = "incentive"
    TENDER = "tender"
    OPEN_DATA = "open_data"
    SITEMAP = "sitemap"


class SignalType(str, enum.Enum):
    NEW_FACILITY = "new_facility"
    EXPANSION = "expansion"
    INVESTMENT = "investment"
    INCENTIVE = "incentive"
    HIRING_WAVE = "hiring_wave"
    INFRASTRUCTURE = "infrastructure_project"
    ENERGY_PROJECT = "energy_project"
    PATENT = "patent"
    PARTNERSHIP = "partnership"
    ACQUISITION = "acquisition"
    SUPPLY_CHAIN = "supply_chain_signal"
    DATA_CENTER = "data_center"
    MINING = "mining"
    SEMICONDUCTOR = "semiconductor"
    AUTOMOTIVE = "automotive"
    DEFENSE = "defense"
    LOGISTICS = "logistics"
    IRRELEVANT = "irrelevant"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


class Industry(str, enum.Enum):
    ENERGY = "enerji"
    DATA_CENTER = "veri_merkezi"
    SEMICONDUCTOR = "yari_iletken"
    AUTOMOTIVE = "otomotiv"
    LOGISTICS = "lojistik"
    MINING = "madencilik"
    MANUFACTURING = "uretim"
    DEFENSE = "savunma"
    CONSTRUCTION = "insaat"
    FINANCE = "finans"
    TECHNOLOGY = "teknoloji"
    AGRICULTURE = "tarim"
    HEALTHCARE = "saglik"
    RETAIL = "perakende"
    TELECOM = "telekom"
    OTHER = "diger"


# ─── Modeller ────────────────────────────────────────────────────────────────

class Source(Base):
    """Veri kaynağı. RSS feed, haber sitesi, devlet duyuru sayfası vb."""
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    base_url = Column(String(500), nullable=False, unique=True)
    feed_url = Column(String(500), nullable=True)  # RSS/Atom URL varsa
    source_type = Column(SAEnum(SourceType), default=SourceType.NEWS_SITE)
    country = Column(String(100), nullable=True, index=True)
    language = Column(String(10), default="tr")
    priority_score = Column(Float, default=0.5)  # 0-1
    trust_score = Column(Float, default=0.5)     # 0-1
    is_active = Column(Boolean, default=True)
    last_checked_at = Column(DateTime, nullable=True)
    check_interval_hours = Column(Float, default=2.0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    articles = relationship("Article", back_populates="source", lazy="dynamic")

    def __repr__(self):
        return f"<Source {self.name}>"


class Article(Base):
    """Ham makale / haber içeriği. Kaynaktan çekilen her içerik."""
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False, index=True)
    title = Column(String(500), nullable=True)
    url = Column(String(1000), nullable=False, unique=True)
    published_at = Column(DateTime, nullable=True, index=True)
    raw_text = Column(Text, nullable=True)
    cleaned_text = Column(Text, nullable=True)
    raw_text_hash = Column(String(64), nullable=True, index=True)
    language = Column(String(10), nullable=True)
    author = Column(String(200), nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    is_processed = Column(Boolean, default=False, index=True)
    processing_attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    source = relationship("Source", back_populates="articles")
    signals = relationship("Signal", back_populates="article", lazy="dynamic")

    __table_args__ = (
        Index("ix_articles_published_source", "published_at", "source_id"),
    )

    def __repr__(self):
        return f"<Article {self.title[:50] if self.title else self.url}>"


class Signal(Base):
    """
    Tespit edilen ekonomik / stratejik sinyal.
    Her makale 0 veya daha fazla sinyal üretebilir.
    """
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False, index=True)

    # Tespit edilen entity bilgileri
    detected_company = Column(String(300), nullable=True, index=True)
    industry = Column(String(100), nullable=True, index=True)
    country = Column(String(100), nullable=True, index=True)
    city_or_region = Column(String(200), nullable=True, index=True)

    # Sinyal sınıflandırması
    signal_type = Column(SAEnum(SignalType), nullable=False, index=True)
    signal_type_label_tr = Column(String(200), nullable=True)  # Türkçe etiket

    # İçerik
    summary_tr = Column(Text, nullable=True)      # Türkçe özet
    evidence_phrases = Column(JSON, nullable=True) # Kanıt cümleleri listesi
    relevant_sectors = Column(JSON, nullable=True) # İlgili sektörler listesi
    keywords_matched = Column(JSON, nullable=True) # Eşleşen keyword'ler

    # Skorlar (0.0 - 1.0)
    confidence_score = Column(Float, default=0.0, index=True)
    impact_score = Column(Float, default=0.0, index=True)
    relevance_score = Column(Float, default=0.0)

    # Bileşik skor - sıralama için
    composite_score = Column(Float, default=0.0, index=True)

    # Tekilleştirme
    duplicate_group_id = Column(String(64), nullable=True, index=True)
    is_duplicate = Column(Boolean, default=False, index=True)

    # İnceleme
    review_status = Column(SAEnum(ReviewStatus), default=ReviewStatus.PENDING, index=True)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_note = Column(Text, nullable=True)

    # AI üretildi mi yoksa kural tabanlı mı?
    detection_method = Column(String(50), default="rules")  # "rules" veya "ai"
    ai_model_used = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    article = relationship("Article", back_populates="signals")
    trend_memberships = relationship("TrendClusterMembership", back_populates="signal")

    __table_args__ = (
        Index("ix_signals_composite", "composite_score", "created_at"),
        Index("ix_signals_industry_type", "industry", "signal_type"),
        Index("ix_signals_country_date", "country", "created_at"),
    )

    def __repr__(self):
        return f"<Signal {self.signal_type} conf={self.confidence_score:.2f}>"


class TrendCluster(Base):
    """
    Tekrar eden sinyal grupları / trend kümeleri.
    Aynı sektör veya bölgede yoğunlaşan gelişmeleri temsil eder.
    """
    __tablename__ = "trend_clusters"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(300), nullable=False)
    description_tr = Column(Text, nullable=True)
    sector = Column(String(100), nullable=True, index=True)
    geography = Column(String(200), nullable=True)
    signal_types = Column(JSON, nullable=True)  # Dahil olan sinyal tipleri
    cluster_score = Column(Float, default=0.0)   # Trendin gücü
    signal_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, index=True)
    first_seen_at = Column(DateTime, nullable=True)
    last_seen_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    memberships = relationship("TrendClusterMembership", back_populates="cluster")

    def __repr__(self):
        return f"<TrendCluster {self.label[:50]}>"


class TrendClusterMembership(Base):
    """Sinyal - TrendCluster ilişkisi."""
    __tablename__ = "trend_cluster_memberships"

    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("trend_clusters.id"), nullable=False)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)

    cluster = relationship("TrendCluster", back_populates="memberships")
    signal = relationship("Signal", back_populates="trend_memberships")


class SystemLog(Base):
    """Sistem olayları ve hata kayıtları."""
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    level = Column(String(20), default="INFO")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<SystemLog {self.event_type} {self.level}>"


class AppSettings(Base):
    """Uygulama ayarları - key/value store."""
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(200), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(String(500), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
