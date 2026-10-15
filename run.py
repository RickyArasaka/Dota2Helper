"""DotaBlitz Launcher and Server Runner."""

import argparse
import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn

BANNER = r"""
  ____        _        ____  _ _ _       
 |  _ \  ___ | |_ __ _| __ )| (_) |_ ____
 | | | |/ _ \| __/ _` |  _ \| | | __|_  /
 | |_| | (_) | || (_| | |_) | | | |_ / / 
 |____/ \___/ \__\__,_|____/|_|_|\__/___|
       Dota 2 Companion App v0.1.0
"""

def open_browser(url: str, delay: float = 1.2):
    time.sleep(delay)
    print(f"\n[DotaBlitz] Opening application in browser: {url}")
    webbrowser.open(url)

def main():
    parser = argparse.ArgumentParser(description="DotaBlitz Companion Runner")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--reload", action="store_true", help="Enable live auto-reload for development")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    args = parser.parse_args()

    print(BANNER)

    # Ensure required data folders exist
    base_dir = Path(__file__).resolve().parent
    (base_dir / "data" / "cache").mkdir(parents=True, exist_ok=True)
    (base_dir / "data" / "cache" / "guides").mkdir(parents=True, exist_ok=True)

    url = f"http://{args.host}:{args.port}"
    print(f"[+] Starting DotaBlitz Companion on {url}")
    print("[+] Waiting for Dota 2 Game State Integration events...")

    if not args.no_browser:
        threading.Thread(target=open_browser, args=(url,), daemon=True).start()

    # Launch uvicorn server
    uvicorn.run(
        "src.backend.app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )

if __name__ == "__main__":
    main()
