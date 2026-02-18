"""
config.py — Application configuration for Phase 1 (hardcoded IPs, local network).

Phase 1 assumptions:
  - Mac and Android TV are on the same WiFi network.
  - TV IP is hardcoded here; no mDNS/discovery yet.
  - Update TV_IP to match your TV's actual local IP before running.
"""

import os

# ---------------------------------------------------------------------------
# TV / Chromecast settings (Phase 1: hardcoded)
# ---------------------------------------------------------------------------
TV_IP: str = os.environ.get("TV_IP", "192.168.29.28")   # ← Android TV LAN IP
TV_NAME: str = os.environ.get("TV_NAME", "Living Room TV")
TV_MAC: str = os.environ.get("TV_MAC", "4c:31:2d:ef:2a:39")  # TV Bluetooth/MAC address

# Mac's own LAN IP — auto-detected by cast_service, but can be overridden here.
# Must be reachable from the TV (same WiFi subnet as TV_IP).
MAC_LOCAL_IP: str = os.environ.get("MAC_LOCAL_IP", "")  # empty = auto-detect

# ---------------------------------------------------------------------------
# Flask settings
# ---------------------------------------------------------------------------
FLASK_PORT: int = int(os.environ.get("FLASK_PORT", 5001))
FLASK_DEBUG: bool = os.environ.get("FLASK_DEBUG", "true").lower() == "true"

# Secret key used by Flask-SocketIO session signing.
# Override via environment variable in production.
SECRET_KEY: str = os.environ.get(
    "SECRET_KEY", "dev-secret-key-change-in-production"
)

# ---------------------------------------------------------------------------
# Frontend (React / Vite dev server)
# ---------------------------------------------------------------------------
REACT_DEV_PORT: int = int(os.environ.get("REACT_DEV_PORT", 3000))

# CORS: allow requests from the React dev server and the Mac's own LAN IP
# (so the TV's receiver can fetch API updates from display.html).
CORS_ORIGINS: list[str] = [
    f"http://localhost:{REACT_DEV_PORT}",
    f"http://127.0.0.1:{REACT_DEV_PORT}",
    # Add a wildcard for local development ease, or specifically add the LAN IP
    "*", 
]

# ---------------------------------------------------------------------------
# PostgreSQL / SQLAlchemy
# ---------------------------------------------------------------------------
# Format: mysql+pymysql://<user>:<password>@<host>/<dbname>?charset=utf8mb4
# PyMySQL is a pure-Python MySQL driver — no C extension needed.
# Homebrew MySQL default: root user with no password.
# Override via DATABASE_URL environment variable in production.
SQLALCHEMY_DATABASE_URI: str = os.environ.get(
    "DATABASE_URL",
    "mysql+pymysql://root:@localhost/textcast_db?charset=utf8mb4",
)
SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

# ---------------------------------------------------------------------------
# Flask-SocketIO
# ---------------------------------------------------------------------------
# eventlet is used as the async mode for non-blocking WebSocket support.
SOCKETIO_ASYNC_MODE: str = "threading"
SOCKETIO_CORS_ALLOWED_ORIGINS: list[str] = CORS_ORIGINS

# ---------------------------------------------------------------------------
# Packet monitoring
# ---------------------------------------------------------------------------
# Maximum number of packet log rows to return in a single stats query.
PACKET_STATS_LIMIT: int = 500

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
