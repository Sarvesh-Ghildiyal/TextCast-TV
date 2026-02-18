"""
cast_routes.py — API endpoints for casting and message history.

Routes:
  POST /api/cast/connect       — connect to TV via PyChromecast and cast display page
  POST /api/cast/send          — send text to TV, log to DB, return latency
  GET  /api/cast/status        — check TV connection status
  GET  /api/cast/current-text  — current text shown on TV (polled by display.html)
  GET  /api/messages/history   — message history from DB

All routes:
  - Return JSON only (no HTML error pages)
  - Log errors with full tracebacks
  - Handle DB failures gracefully (cast still works even if DB is down)

Connection flow:
  1. Frontend calls POST /api/cast/connect  (or user clicks "Connect" button)
  2. Backend calls cast_service.init_chromecast() — TLS handshake on port 8009
  3. Backend calls cast_service.cast_display_page() — TV opens display.html
  4. Frontend calls POST /api/cast/send with text
  5. display.html polls /api/cast/current-text every 2s and updates the DOM
"""

import logging
import time
from typing import Optional

from flask import Blueprint, current_app, jsonify, request

import config
from services import cast_service, db_service, packet_monitor

logger = logging.getLogger(__name__)

cast_bp = Blueprint("cast", __name__)

# ---------------------------------------------------------------------------
# Module-level active session tracker
# ---------------------------------------------------------------------------
# We maintain one "active session" per application lifetime (Phase 1).
# The session is created lazily on the first successful cast send.
# A more sophisticated approach (per-connection sessions) is deferred to Phase 2.
_active_session_id: Optional[int] = None

# True once cast_display_page() has been called successfully this session.
# Prevents re-casting the page on every send (which would reload the TV browser).
_cast_page_sent: bool = False


def _get_or_create_session() -> Optional[int]:
    """
    Return the active session ID, creating one if needed.

    Lazily upserts the TV device and opens a session on first call.
    Returns None if the DB is unavailable.
    """
    global _active_session_id

    if _active_session_id is not None:
        return _active_session_id

    try:
        device = db_service.get_or_create_device(
            name=config.TV_NAME,
            ip_address=config.TV_IP,
            mac_address=config.TV_MAC,
        )
        if device is None:
            return None

        session = db_service.create_session(
            device_id=device.id,
            connection_type="local",
        )
        if session is None:
            return None

        _active_session_id = session.id
        logger.info("Active session created: id=%d", _active_session_id)

        # Start packet monitor now that we have a real session ID.
        # Requires sudo (raw socket) — silently skips if already running.
        if not packet_monitor.is_running():
            app = current_app._get_current_object()
            started = packet_monitor.start_monitor(_active_session_id, app)
            logger.info("Packet monitor start_monitor() returned: %s", started)

        return _active_session_id

    except Exception as exc:
        logger.error("Failed to create DB session: %s", exc, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# POST /api/cast/connect
# ---------------------------------------------------------------------------

@cast_bp.post("/cast/connect")
def connect_to_tv():
    """
    Initiate a PyChromecast connection to the TV and cast the display page.

    This is the FIRST call the frontend should make before sending text.
    It performs:
      1. PyChromecast TCP/TLS handshake on TV_IP:8009
      2. Casts display.html to the TV's Default Media Receiver
      3. Creates a DB session (for logging)
      4. Starts the Scapy packet monitor

    Safe to call multiple times — reconnects if already connected.

    Response 200 (JSON):
      { "success": true, "message": "Connected and display page cast to TV" }

    Response 503 (JSON):
      { "success": false, "error": "Could not connect to TV at 192.168.29.28" }
    """
    global _cast_page_sent

    logger.info("POST /api/cast/connect — connecting to TV at %s", config.TV_IP)

    # Step 1: Connect via PyChromecast
    connected = cast_service.init_chromecast(timeout=10)
    if not connected:
        return jsonify({
            "success": False,
            "error": f"Could not connect to TV at {config.TV_IP}. "
                     "Make sure the TV is on, on the same WiFi, and Chromecast is enabled."
        }), 503

    # Step 2: Cast the display page to the TV
    casted = cast_service.cast_display_page()
    if casted:
        _cast_page_sent = True
        logger.info("Display page cast successfully")
    else:
        logger.warning("Connected to TV but failed to cast display page")

    # Step 3: Create DB session + start packet monitor (best-effort)
    try:
        session_id = _get_or_create_session()
        logger.info("Session ready: id=%s", session_id)
    except Exception as exc:
        logger.warning("DB session creation failed (non-fatal): %s", exc)

    return jsonify({
        "success": True,
        "message": "Connected to TV and display page cast successfully" if casted
                   else "Connected to TV (display page cast failed — check logs)",
        "tv_ip": config.TV_IP,
        "tv_name": config.TV_NAME,
        "display_cast": casted,
    })


# ---------------------------------------------------------------------------
# POST /api/cast/disconnect
# ---------------------------------------------------------------------------

@cast_bp.post("/cast/disconnect")
def disconnect_from_tv():
    """
    Gracefully disconnect from the Chromecast and stop the packet monitor.

    Response 200 (JSON):
      { "success": true, "message": "Disconnected from TV" }
    """
    try:
        cast_service.disconnect()
        return jsonify({
            "success": True,
            "message": "Disconnected from TV",
        })
    except Exception as exc:
        logger.error("Error during disconnect: %s", exc, exc_info=True)
        return jsonify({
            "success": False,
            "error": "Failed to disconnect cleanly",
            "detail": str(exc)
        }), 500


# ---------------------------------------------------------------------------
# POST /api/cast/send
# ---------------------------------------------------------------------------

@cast_bp.post("/cast/send")
def send_text():
    """
    Receive text from the React frontend and display it on the TV.

    Flow:
      1. Validate request body
      2. Record start time for latency measurement
      3. Call cast_service.update_display_text() — updates in-memory text
         that display.html polls every 2 seconds
      4. Calculate round-trip latency (time from request receipt to text update)
      5. Log message to DB (non-blocking — DB failure doesn't fail the cast)
      6. Return JSON with success flag and latency

    Request body (JSON):
      { "text": "Hello, TV!" }

    Response 200 (JSON):
      { "success": true, "latency_ms": 12.3, "message_id": 42 }

    Response 400 (JSON):
      { "error": "Missing 'text' field in request body" }

    Response 500 (JSON):
      { "error": "Failed to send text to TV", "detail": "..." }
    """
    # --- Validate input ----------------------------------------------------
    data = request.get_json(silent=True)
    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' field in request body"}), 400

    text = str(data["text"]).strip()
    if not text:
        return jsonify({"error": "'text' must not be empty"}), 400

    # --- Send to TV --------------------------------------------------------
    t_start = time.monotonic()

    # Auto-connect if not yet connected (convenience: works even without
    # calling /api/cast/connect first, but /api/cast/connect is preferred).
    status = cast_service.get_connection_status()
    if not status["online"]:
        logger.info("TV not connected — attempting auto-connect before send")
        cast_service.init_chromecast(timeout=10)

    # Auto-cast the display page if this is the first send this session.
    global _cast_page_sent
    if not _cast_page_sent:
        casted = cast_service.cast_display_page()
        if casted:
            _cast_page_sent = True
            logger.info("Display page auto-cast on first send")

    try:
        cast_service.update_display_text(text)
    except Exception as exc:
        logger.error("cast_service.update_display_text failed: %s", exc, exc_info=True)
        return jsonify({"error": "Failed to send text to TV", "detail": str(exc)}), 500

    # Latency = time from request arrival to text being stored in memory
    # (display.html will pick it up within its next 2-second poll cycle)
    latency_ms = (time.monotonic() - t_start) * 1000

    # --- Log to DB (best-effort — don't fail the cast if DB is down) -------
    message_id = None
    try:
        session_id = _get_or_create_session()
        if session_id is not None:
            msg = db_service.log_message(
                session_id=session_id,
                text=text,
                delivered=True,
                latency_ms=round(latency_ms, 2),
            )
            if msg:
                message_id = msg.id
    except Exception as db_exc:
        logger.warning("DB log failed (cast still succeeded): %s", db_exc)

    logger.info("Text sent to TV: %r (latency=%.1fms)", text[:60], latency_ms)

    return jsonify({
        "success": True,
        "latency_ms": round(latency_ms, 2),
        "message_id": message_id,
    })


# ---------------------------------------------------------------------------
# GET /api/cast/status
# ---------------------------------------------------------------------------

@cast_bp.get("/cast/status")
def cast_status():
    """
    Return the current TV connection status.

    Calls cast_service.get_connection_status() which checks the live
    PyChromecast connection object (no network round-trip if already connected).

    Response 200 (JSON):
      {
        "online": true,
        "device_name": "Living Room TV",
        "device_ip": "192.168.1.100",
        "model_name": "Android TV"
      }
    """
    try:
        status = cast_service.get_connection_status()
        return jsonify(status)
    except Exception as exc:
        logger.error("Error checking cast status: %s", exc, exc_info=True)
        return jsonify({
            "error": "Could not determine TV status",
            "detail": str(exc),
            "online": False,
            "device_name": config.TV_NAME,
            "device_ip": config.TV_IP,
        }), 500


# ---------------------------------------------------------------------------
# GET /api/cast/current-text
# ---------------------------------------------------------------------------

@cast_bp.get("/tv/heartbeat")
def tv_heartbeat():
    """
    Heartbeat endpoint for the TV display.
    Logs that the TV's browser has successfully executed JavaScript.
    """
    logger.info("TV HEARTBEAT RECEIVED - JS is executing on the TV!")
    return jsonify({"status": "ok"})


@cast_bp.get("/cast/current-text")
def get_current_text():
    """
    Return the text currently stored for TV display.

    Polled by display.html every 2 seconds from the TV's browser.
    Must be fast — no DB query, just reads from in-memory state.
    Response 200 (JSON):
      { "text": "Hello, TV!" }
    """
    try:
        text = cast_service.get_current_text()
        return jsonify({"text": text})
    except Exception as exc:
        logger.error("Error fetching current text: %s", exc, exc_info=True)
        return jsonify({"error": "Could not fetch current text", "text": ""}), 500


# ---------------------------------------------------------------------------
# GET /api/messages/history
# ---------------------------------------------------------------------------

@cast_bp.get("/messages/history")
def message_history():
    """
    Return the most recent messages sent to the TV.

    Query params:
      limit (int, 1–100, default 20)

    Response 200 (JSON):
      {
        "messages": [
          {
            "id": 1,
            "session_id": 1,
            "text": "Hello, TV!",
            "timestamp": "2026-02-18T14:30:00+00:00",
            "delivered": true,
            "latency_ms": 12.3
          },
          ...
        ],
        "count": 5
      }
    """
    try:
        limit = int(request.args.get("limit", 20))
        limit = max(1, min(limit, 100))  # clamp to [1, 100]
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid 'limit' parameter — must be an integer"}), 400

    try:
        messages = db_service.get_message_history(limit=limit)
        return jsonify({"messages": messages, "count": len(messages)})
    except Exception as exc:
        logger.error("Error fetching message history: %s", exc, exc_info=True)
        return jsonify({"error": "Could not fetch message history", "messages": []}), 500
