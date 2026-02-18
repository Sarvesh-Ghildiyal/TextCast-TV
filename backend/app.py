"""
app.py — Main Flask application entry point for the Text-to-TV Display System.

Initialises:
  - Flask with CORS
  - Flask-SocketIO (eventlet async mode)
  - Flask-SQLAlchemy (shared `db` from models.py)
  - Flask-Migrate (Alembic-based migrations)

Blueprints:
  - cast_routes    → /api/cast/*  and /api/messages/*
  - monitor_routes → /api/packets/*

IMPORTANT — async mode:
  We use async_mode='threading' (standard Python threads) instead of eventlet.
  This avoids the monkey_patch() ordering problem entirely — threading mode
  works with Flask's built-in dev server and requires no patching at all.

  To switch to eventlet for production, update config.SOCKETIO_ASYNC_MODE
  and use wsgi.py as the entry point (which calls monkey_patch() first).
"""

import logging
import sys

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_migrate import Migrate
from flask_socketio import SocketIO

import config
from models import db
from services import packet_monitor

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Extensions (initialised without app — attached in create_app())
# ---------------------------------------------------------------------------
socketio = SocketIO()
migrate = Migrate()


def create_app() -> Flask:
    """
    Application factory.

    Returns a fully configured Flask application instance.
    Using the factory pattern makes the app testable and avoids circular imports.
    """
    app = Flask(__name__)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = config.SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = config.SQLALCHEMY_TRACK_MODIFICATIONS

    # ------------------------------------------------------------------
    # Extensions
    # ------------------------------------------------------------------

    # CORS — allow React dev server to call Flask APIs
    CORS(app, origins=config.CORS_ORIGINS, supports_credentials=True)
    logger.info("CORS enabled for origins: %s", config.CORS_ORIGINS)

    # SQLAlchemy
    db.init_app(app)
    logger.info("SQLAlchemy initialised with URI: %s", config.SQLALCHEMY_DATABASE_URI)

    # Flask-Migrate (Alembic)
    migrate.init_app(app, db)
    logger.info("Flask-Migrate initialised")

    # Flask-SocketIO
    # async_mode=eventlet requires monkey_patch() to have been called BEFORE
    # this point (done in wsgi.py / __main__ block, not here).
    socketio.init_app(
        app,
        async_mode=config.SOCKETIO_ASYNC_MODE,
        cors_allowed_origins=config.SOCKETIO_CORS_ALLOWED_ORIGINS,
        logger=False,
        engineio_logger=False,
    )
    logger.info("Flask-SocketIO initialised (async_mode=%s)", config.SOCKETIO_ASYNC_MODE)

    # Inject the SocketIO instance into packet_monitor so the background
    # capture thread can emit 'packet_update' WebSocket events.
    packet_monitor.set_socketio(socketio)

    # ------------------------------------------------------------------
    # Blueprints
    # ------------------------------------------------------------------
    _register_blueprints(app)

    # ------------------------------------------------------------------
    # Health-check route
    # ------------------------------------------------------------------
    @app.get("/api/health")
    def health():
        """Simple liveness probe — returns 200 if Flask is running."""
        return jsonify({"status": "ok", "service": "text-to-tv-backend"})

    @app.get("/display")
    def display():
        """
        Serve the TV display page.

        This is the URL that PyChromecast casts to the TV:
            http://<MAC_LOCAL_IP>:<FLASK_PORT>/display

        The TV's built-in Chromecast receiver opens this URL in a full-screen
        browser. The page polls /api/cast/current-text every 2 seconds and
        updates the displayed text without a full page reload.
        """
        from services import cast_service
        mac_ip = cast_service.get_mac_local_ip()
        return render_template(
            "display.html",
            mac_ip=mac_ip,
            port=config.FLASK_PORT
        )

    @app.after_request
    def add_pna_headers(response):
        """
        Add Private Network Access (PNA) headers.
        Crucial for modern browsers communicating with local IPs.
        """
        response.headers["Access-Control-Allow-Private-Network"] = "true"
        # Also handle preflight (OPTIONS) requests if any
        if request.method == "OPTIONS":
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Requested-With"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response

    # Stop the packet monitor cleanly on process exit (NOT on teardown_appcontext,
    # which fires after every request and would kill the monitor immediately).
    import atexit
    atexit.register(lambda: packet_monitor.stop_monitor(timeout=3.0))

    logger.info("Flask application created successfully")
    return app


def _register_blueprints(app: Flask) -> None:
    """
    Register all route blueprints.

    Import is deferred inside this function to avoid circular imports
    (blueprints may import `db`, `socketio`, etc. from this module).
    """
    try:
        from routes.cast_routes import cast_bp
        app.register_blueprint(cast_bp, url_prefix="/api")
        logger.info("Registered blueprint: cast_routes → /api")
    except ImportError as exc:
        logger.warning("cast_routes not yet available: %s", exc)

    try:
        from routes.monitor_routes import monitor_bp
        app.register_blueprint(monitor_bp, url_prefix="/api")
        logger.info("Registered blueprint: monitor_routes → /api")
    except ImportError as exc:
        logger.warning("monitor_routes not yet available: %s", exc)


# ---------------------------------------------------------------------------
# Module-level app instance — required by Flask CLI (FLASK_APP=app.py)
# ---------------------------------------------------------------------------
# Flask CLI discovers the app via this variable when FLASK_APP=app.py is set.
# It does NOT trigger monkey_patch() — safe for `flask db` commands.
app = create_app()


# ---------------------------------------------------------------------------
# Direct run entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info(
        "Starting Flask-SocketIO server on port %d (debug=%s)",
        config.FLASK_PORT,
        config.FLASK_DEBUG,
    )

    # socketio.run() replaces app.run() when using Flask-SocketIO.
    # threading async_mode works with the standard Werkzeug dev server —
    # no monkey_patch() required.
    socketio.run(
        app,
        host="0.0.0.0",
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
        allow_unsafe_werkzeug=True,  # required for Flask-SocketIO + Werkzeug dev server
    )
