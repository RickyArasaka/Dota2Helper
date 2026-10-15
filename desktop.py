"""DotaBlitz Native Desktop Application Window Launcher."""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Redirect stdout/stderr if None (in PyInstaller noconsole mode)
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

# Configure file logging so we can always diagnose issues
log_file = Path(sys.executable).parent / "dotablitz.log" if getattr(sys, "frozen", False) else Path("dotablitz.log")
logging.basicConfig(
    filename=str(log_file),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("dotablitz.desktop")

import uvicorn
from src.backend.app.main import app

def start_backend_server():
    """Run uvicorn server passing the direct app instance (essential for PyInstaller)."""
    try:
        logger.info("Starting uvicorn server in background thread...")
        config = uvicorn.Config(
            app=app,
            host="127.0.0.1",
            port=8000,
            log_level="info",
            loop="asyncio",
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception as exc:
        logger.error("Failed to start backend server: %s", exc, exc_info=True)

def main():
    logger.info("Initializing DotaBlitz launcher...")
    
    # Ensure data directory exists
    base_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    (base_dir / "data" / "cache").mkdir(parents=True, exist_ok=True)
    (base_dir / "data" / "cache" / "guides").mkdir(parents=True, exist_ok=True)

    # Automatically install / verify Dota 2 GSI configuration
    try:
        from scripts.install_gsi import install as install_gsi
        install_gsi()
    except Exception as e:
        logger.warning("Could not auto-install GSI: %s", e)

    # Start FastAPI backend in a daemon thread
    server_thread = threading.Thread(target=start_backend_server, daemon=True)
    server_thread.start()

    # Wait for the server to be ready on port 8000
    app_url = "http://127.0.0.1:8000"
    import urllib.request
    server_ready = False
    for attempt in range(20):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen(f"{app_url}/api/health", timeout=1) as resp:
                if resp.status == 200:
                    server_ready = True
                    logger.info("Server is up and responding on attempt %d", attempt + 1)
                    break
        except Exception:
            pass

    if not server_ready:
        logger.warning("Server took longer than expected to report healthy, proceeding anyway...")

    # Attempt to open desktop window with pywebview
    opened_webview = False
    try:
        import webview
        logger.info("pywebview available, creating native window...")
        window = webview.create_window(
            title="DotaBlitz – Dota 2 Companion",
            url=app_url,
            width=1280,
            height=820,
            min_size=(960, 640),
            background_color="#0a0e14",
        )
        opened_webview = True
        webview.start()
    except Exception as exc:
        logger.warning("pywebview could not launch native window (%s), falling back to browser.", exc)

    if not opened_webview:
        logger.info("Opening browser fallback: %s", app_url)
        webbrowser.open(app_url)
        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            logger.info("DotaBlitz shutting down...")

if __name__ == "__main__":
    main()
