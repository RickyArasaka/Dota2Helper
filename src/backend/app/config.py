import sys
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# If packaged with PyInstaller, sys._MEIPASS contains embedded static assets
if getattr(sys, "frozen", False):
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path.cwd()))
    APP_DIR = Path(sys.executable).parent
else:
    BUNDLE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    APP_DIR = BUNDLE_DIR

BASE_DIR = APP_DIR


class Settings(BaseSettings):
    """Global application settings, loaded from .env or environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(APP_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{APP_DIR / 'data' / 'cache' / 'dotablitz.db'}"

    # External APIs
    OPENDOTA_API_BASE: str = "https://api.opendota.com/api"
    STRATZ_API_BASE: str = "https://api.stratz.com/api/v1"
    OPENDOTA_API_KEY: str = ""
    STRATZ_API_KEY: str = ""

    # Cache
    CACHE_TTL_HOURS: int = 6

    # Recommendation weights (should sum to 1.0)
    WEIGHT_OPENDOTA: float = 0.5
    WEIGHT_DOTABUFF: float = 0.3
    WEIGHT_DOTAFIRE: float = 0.2

    # Minimum sample size for a build to be considered valid
    MIN_SAMPLE_SIZE: int = 50

    # GSI
    GSI_AUTH_TOKEN: str = "dotablitz_secret_token"

    # Paths (static assets from bundle, persistent data from app directory)
    DATA_DIR: Path = APP_DIR / "data" / "cache"
    FRONTEND_DIR: Path = BUNDLE_DIR / "src" / "frontend"
    GSI_CFG_DIR: Path = BUNDLE_DIR / "data" / "gsi"


settings = Settings()
