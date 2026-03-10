# OpenSignal Radar TR

**Açık Kaynak Ekonomik Sinyal Tespit Platformu**

Kamuya açık verileri tarayarak ekonomik, endüstriyel ve stratejik sinyalleri tespit eden, tamamen ücretsiz ve yerel çalışabilen bir istihbarat platformu.

---

## Temel Özellikler

- Çok kaynaklı veri toplama (RSS, web scraping, basın odaları, devlet duyuruları)
- Kural tabanlı sinyal tespit motoru (API gerektirmez)
- Opsiyonel Ollama entegrasyonu ile AI destekli analiz
- Ultra-premium Türkçe yönetici arayüzü
- Executive Intelligence Deck görünümü
- Trend ve kümelenme analizi
- JSON/CSV export

## Kurulum

```bash
# 1. Bağımlılıkları kur
pip install -r requirements.txt

# 2. Playwright tarayıcılarını kur (opsiyonel, JS-ağır siteler için)
playwright install chromium

# 3. Veritabanını başlat
python -m backend.core.database

# 4. Başlangıç kaynaklarını yükle
python scripts/seed_sources.py

# 5. Uygulamayı başlat
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Tarayıcıda `http://localhost:8000` adresine git.

## Opsiyonel: Ollama AI Entegrasyonu

```bash
# Ollama kur (ollama.ai)
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen2.5:7b-instruct
```

Ollama çalışıyorsa sistem otomatik olarak AI modunu aktif eder.

## Teknik Yığın

- **Backend**: Python, FastAPI, SQLAlchemy, SQLite
- **Veri Toplama**: feedparser, httpx, BeautifulSoup, trafilatura, Playwright
- **Zamanlama**: APScheduler
- **AI (opsiyonel)**: Ollama (qwen2.5, llama tabanlı modeller)
- **Frontend**: Jinja2, özel CSS, vanilla JS

## Lisans

MIT
