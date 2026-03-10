"""
Hızlı kurulum scripti.
python scripts/setup.py komutu ile çalıştırılır.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("\n" + "="*60)
    print("  OpenSignal Radar TR — Kurulum")
    print("="*60)

    # 1. Veritabanını başlat
    print("\n[1/3] Veritabanı başlatılıyor...")
    from backend.db.database import init_db
    init_db()
    print("  ✓ Veritabanı hazır")

    # 2. Kaynakları yükle
    print("\n[2/3] Başlangıç kaynakları yükleniyor...")
    from scripts.seed_sources import seed
    added = seed()
    print(f"  ✓ {added} yeni kaynak eklendi")

    # 3. Demo veri (opsiyonel)
    if "--demo" in sys.argv:
        print("\n[3/3] Demo veri oluşturuluyor...")
        from scripts.demo_data import create_demo_data
        create_demo_data()
    else:
        print("\n[3/3] Demo veri atlandı (--demo ile ekleyebilirsiniz)")

    print("\n" + "="*60)
    print("  Kurulum tamamlandı!")
    print("\n  Uygulamayı başlatmak için:")
    print("  uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
    print("\n  Tarayıcıda aç: http://localhost:8000")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
