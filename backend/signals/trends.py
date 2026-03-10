"""
Trend ve kümelenme analizi.
Tekrar eden sinyalleri tespit eder ve TrendCluster oluşturur.
"""
import logging
from collections import Counter
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.db.models import Signal, TrendCluster, TrendClusterMembership, ReviewStatus

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """
    Son N günlük sinyalleri analiz ederek trend kümeleri oluşturur.
    """

    def __init__(self, db: Session, lookback_days: int = 14):
        self.db = db
        self.lookback_days = lookback_days
        self.since = datetime.utcnow() - timedelta(days=lookback_days)

    def run(self) -> int:
        """Tüm trend analizini çalıştır. Kaç küme güncellendi/oluşturuldu döndür."""
        relevant_signals = (
            self.db.query(Signal)
            .filter(Signal.created_at >= self.since)
            .filter(Signal.is_duplicate == False)
            .filter(Signal.review_status != ReviewStatus.REJECTED)
            .filter(Signal.composite_score >= 0.35)
            .all()
        )

        if len(relevant_signals) < 3:
            return 0

        clusters_updated = 0

        # 1. Sektör bazlı trend kümeleri
        clusters_updated += self._cluster_by_sector(relevant_signals)

        # 2. Coğrafya bazlı kümeleme
        clusters_updated += self._cluster_by_geography(relevant_signals)

        # 3. Sinyal tipi bazlı kümeleme
        clusters_updated += self._cluster_by_signal_type(relevant_signals)

        self.db.commit()
        logger.info(f"Trend analizi tamamlandı: {clusters_updated} küme güncellendi")
        return clusters_updated

    def _cluster_by_sector(self, signals: List[Signal]) -> int:
        """Aynı sektörde 3+ sinyal varsa trend kümesi oluştur."""
        sector_signals: Dict[str, List[Signal]] = {}
        for sig in signals:
            if sig.industry:
                sector_signals.setdefault(sig.industry, []).append(sig)

        count = 0
        for sector, sigs in sector_signals.items():
            if len(sigs) >= 3:
                self._upsert_cluster(
                    label=f"{sector.capitalize()} sektöründe yoğunlaşma",
                    description=self._describe_sector_cluster(sector, sigs),
                    sector=sector,
                    geography=None,
                    signals=sigs,
                    cluster_type="sector",
                )
                count += 1
        return count

    def _cluster_by_geography(self, signals: List[Signal]) -> int:
        """Aynı ülkede 4+ sinyal varsa coğrafi küme oluştur."""
        geo_signals: Dict[str, List[Signal]] = {}
        for sig in signals:
            if sig.country:
                geo_signals.setdefault(sig.country, []).append(sig)

        count = 0
        for country, sigs in geo_signals.items():
            if len(sigs) >= 4:
                # Bu ülkedeki dominant sektörü bul
                sectors = [s.industry for s in sigs if s.industry]
                dominant = Counter(sectors).most_common(1)
                dominant_sector = dominant[0][0] if dominant else None

                self._upsert_cluster(
                    label=f"{country}'de yatırım ivmesi",
                    description=self._describe_geo_cluster(country, sigs),
                    sector=dominant_sector,
                    geography=country,
                    signals=sigs,
                    cluster_type="geography",
                )
                count += 1
        return count

    def _cluster_by_signal_type(self, signals: List[Signal]) -> int:
        """Aynı sinyal tipinde 5+ sinyal varsa pattern oluştur."""
        from backend.signals.keywords import SIGNAL_TYPE_LABELS_TR
        type_signals: Dict[str, List[Signal]] = {}
        for sig in signals:
            type_signals.setdefault(sig.signal_type.value, []).append(sig)

        count = 0
        for sig_type, sigs in type_signals.items():
            if len(sigs) >= 5:
                label_tr = SIGNAL_TYPE_LABELS_TR.get(
                    next(s.signal_type for s in sigs), sig_type
                )
                self._upsert_cluster(
                    label=f"Gelişen örüntü: {label_tr}",
                    description=self._describe_type_cluster(sig_type, sigs),
                    sector=None,
                    geography=None,
                    signals=sigs,
                    cluster_type="signal_type",
                )
                count += 1
        return count

    def _upsert_cluster(
        self,
        label: str,
        description: str,
        sector,
        geography,
        signals: List[Signal],
        cluster_type: str,
    ) -> TrendCluster:
        """Kümeyi oluştur veya güncelle."""
        # Mevcut aktif kümeyi bul
        existing = (
            self.db.query(TrendCluster)
            .filter(TrendCluster.label == label)
            .filter(TrendCluster.is_active == True)
            .first()
        )

        avg_score = (
            sum(s.composite_score for s in signals) / len(signals)
            if signals else 0.0
        )

        if existing:
            existing.signal_count = len(signals)
            existing.cluster_score = avg_score
            existing.description_tr = description
            existing.last_seen_at = datetime.utcnow()
            existing.updated_at = datetime.utcnow()
            cluster = existing
        else:
            cluster = TrendCluster(
                label=label,
                description_tr=description,
                sector=sector.value if hasattr(sector, 'value') else sector,
                geography=geography,
                cluster_score=avg_score,
                signal_count=len(signals),
                is_active=True,
                first_seen_at=datetime.utcnow(),
                last_seen_at=datetime.utcnow(),
            )
            self.db.add(cluster)
            self.db.flush()

        # Üyelikleri güncelle
        for sig in signals:
            existing_membership = (
                self.db.query(TrendClusterMembership)
                .filter(TrendClusterMembership.cluster_id == cluster.id)
                .filter(TrendClusterMembership.signal_id == sig.id)
                .first()
            )
            if not existing_membership:
                membership = TrendClusterMembership(
                    cluster_id=cluster.id,
                    signal_id=sig.id,
                )
                self.db.add(membership)

        return cluster

    def _describe_sector_cluster(self, sector: str, signals: List[Signal]) -> str:
        countries = list({s.country for s in signals if s.country})[:3]
        country_str = ", ".join(countries) if countries else "çeşitli ülkelerde"
        return (
            f"Son {self.lookback_days} günde {sector} sektöründe "
            f"{len(signals)} sinyal tespit edildi. "
            f"Öne çıkan coğrafyalar: {country_str}. "
            f"Bu yoğunlaşma, sektörde güçlü bir yatırım momentumu işaret etmektedir."
        )

    def _describe_geo_cluster(self, country: str, signals: List[Signal]) -> str:
        sectors = list({s.industry for s in signals if s.industry})[:3]
        sector_str = ", ".join(sectors) if sectors else "çeşitli sektörlerde"
        return (
            f"{country}'de son {self.lookback_days} günde "
            f"{len(signals)} stratejik sinyal kaydedildi. "
            f"Aktif sektörler: {sector_str}. "
            f"Ülke, bu dönemde güçlü bir yatırım aktivitesi sergiliyor."
        )

    def _describe_type_cluster(self, sig_type: str, signals: List[Signal]) -> str:
        countries = list({s.country for s in signals if s.country})[:3]
        country_str = ", ".join(countries) if countries else "global ölçekte"
        return (
            f"Son {self.lookback_days} günde '{sig_type}' kategorisinde "
            f"{len(signals)} sinyal tespit edildi. "
            f"Coğrafi dağılım: {country_str}. "
            f"Bu örüntü, ilgili alanda yapısal bir momentum işaret etmektedir."
        )
