"""
Uygulamayı başlatır ve yerel ağ IP adresini gösterir.
python scripts/start.py
"""
import socket
import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_local_ip() -> str:
    """Bilgisayarın yerel ağ IP adresini bul."""
    try:
        # Dış bağlantı gerektirmez, sadece routing tablosunu okur
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    port = 8000

    # Komut satırı argümanı ile port değiştirilebilir
    for arg in sys.argv[1:]:
        if arg.startswith("--port="):
            port = int(arg.split("=")[1])

    local_ip = get_local_ip()

    print("\n" + "=" * 60)
    print("  OpenSignal Radar TR")
    print("=" * 60)
    print(f"\n  Bu bilgisayarda aç:")
    print(f"  → http://localhost:{port}")
    print(f"\n  Tabletinden / telefonundan aç:")
    print(f"  → http://{local_ip}:{port}")
    print(f"\n  Not: Tablet ve bilgisayar aynı Wi-Fi ağında olmalı.")
    print("=" * 60 + "\n")

    # Uvicorn başlat
    os.execlp(
        "uvicorn",
        "uvicorn",
        "backend.main:app",
        "--host", "0.0.0.0",
        "--port", str(port),
        "--reload",
    )


if __name__ == "__main__":
    main()
