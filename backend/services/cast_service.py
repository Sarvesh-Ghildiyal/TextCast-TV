"""
cast_service.py — PyChromecast integration for the Text-to-TV Display System.

HOW PYCHROMECAST CONNECTS
--------------------------
PyChromecast communicates with a Chromecast device over the local network using
the Google Cast protocol (a proprietary protocol over TLS/TCP on port 8009).

Two discovery methods exist:
  1. mDNS/Zeroconf discovery  — scans the network for Cast devices (Phase 2+)
  2. Direct IP connection     — connects to a known IP:port immediately (Phase 1)

We use method 2 (direct IP) via `pychromecast.get_chromecast_from_host()`.
This skips mDNS entirely and is reliable when the TV IP is static/hardcoded.

WHAT RECEIVER IT USES
----------------------
Every Chromecast device has a "Default Media Receiver" built in — a generic
web-based receiver that can load and display any URL.

App ID: "CC1AD845"  (Google's Default Media Receiver)

When we call `cast.media_controller.play_media(url, "text/html")`, the
Chromecast:
  1. Opens the Default Media Receiver app on the TV
  2. Loads the given URL in a full-screen Chromium browser
  3. The browser renders our display.html page

HOW THE PAGE URL IS CONSTRUCTED
---------------------------------
Flask serves display.html at:
    http://<MAC_LOCAL_IP>:<FLASK_PORT>/display

The TV's Chromecast receiver fetches this URL from the Mac's Flask server.
Both devices must be on the same WiFi network (Phase 1 assumption).

The Mac's local IP is auto-detected at startup using socket.gethostbyname(),
or can be overridden via config.MAC_LOCAL_IP.

TEXT UPDATE FLOW
-----------------
1. React frontend sends POST /api/cast/send with {"text": "Hello"}
2. cast_route calls update_display_text("Hello")
3. This module stores the text in _current_text (in-memory)
4. display.html polls GET /api/cast/current-text every 2 seconds
5. The TV's browser updates the DOM — no page reload, no re-cast needed
"""

import logging
import socket
import threading
import time
from typing import Optional

import pychromecast
from pychromecast import Chromecast
from pychromecast.error import ChromecastConnectionError
from pychromecast.controllers.dashcast import DashCastController

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

# The active Chromecast connection object.
# None until init_chromecast() succeeds.
_cast: Optional[Chromecast] = None

# Lock protecting _cast — init_chromecast() may be called from a background
# thread; routes read _cast concurrently.
_cast_lock = threading.Lock()

# The text currently displayed on the TV.
# Updated by update_display_text(); read by the /api/cast/current-text route
# which display.html polls every 2 seconds.
_current_text: str = ""
_text_lock = threading.RLock()

# Tracker for whether we've successfully initiated a cast session.
_cast_page_sent: bool = False

# The App ID that was running on the TV before we started casting.
# This allows us to return the TV to its previous state on disconnect.
_prev_app_id: Optional[str] = None

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def get_mac_local_ip() -> str:
    """
    Detect the Mac's local network IP address.

    Opens a UDP socket toward the TV IP (no data is sent) and reads the
    source address the OS would use for that route. This is the most reliable
    way to get the correct interface IP on a multi-homed machine.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect((config.TV_IP, 8009))  # 8009 = Cast protocol port
            return s.getsockname()[0]
    except OSError:
        # Fallback: hostname resolution (less reliable on M1 with VPN)
        return socket.gethostbyname(socket.gethostname())


def _build_display_url() -> str:
    """
    Construct the URL that the TV's Chromecast receiver will load.

    Format: http://<MAC_LOCAL_IP>:<FLASK_PORT>/display?t=<timestamp>

    The TV fetches this URL from the Mac's Flask server, so both devices
    must be on the same WiFi network (Phase 1 assumption).
    """
    mac_ip = get_mac_local_ip()
    # Add a timestamp to bypass any potential caching in the TV's browser
    url = f"http://{mac_ip}:{config.FLASK_PORT}/display?t={int(time.time())}"
    logger.debug("Display URL: %s", url)
    return url


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init_chromecast(timeout: int = 10) -> bool:
    """
    Connect to the Android TV using its hardcoded IP address.

    PyChromecast's get_chromecast_from_host() performs a direct TCP connection
    to <TV_IP>:8009 (the Cast protocol port) without any mDNS discovery.
    This is the correct approach for Phase 1 where the IP is known.

    Args:
        timeout: Seconds to wait for the connection handshake.

    Returns:
        True if connection succeeded, False otherwise.
    """
    global _cast

    logger.info(
        "Connecting to Chromecast at %s (name: %s, timeout: %ds)...",
        config.TV_IP,
        config.TV_NAME,
        timeout,
    )

    try:
        # get_chromecast_from_host() accepts a tuple:
        #   (host, port, uuid, model_name, friendly_name)
        # Port 8009 is the standard Cast protocol port.
        # uuid/model_name/friendly_name can be None for direct IP connections.
        # PyChromecast 13.x: get_chromecast_from_host() returns a single
        # Chromecast object (not a tuple). The host tuple format is:
        #   (host, port, uuid, model_name, friendly_name)
        cast = pychromecast.get_chromecast_from_host(
            (config.TV_IP, 8009, None, None, config.TV_NAME),
            timeout=timeout,
        )

        # wait() blocks until the TLS handshake and Cast protocol
        # negotiation complete, or until timeout is reached.
        cast.wait(timeout=timeout)

        with _cast_lock:
            _cast = cast

        logger.info(
            "Connected to Chromecast: %s (model: %s, uuid: %s)",
            cast.name,
            cast.model_name,
            cast.uuid,
        )

        return True

    except ChromecastConnectionError as exc:
        logger.error("Chromecast connection error: %s", exc)
        return False
    except pychromecast.error.NotConnected as exc:
        logger.error("Chromecast not connected: %s", exc)
        return False
    except Exception as exc:
        # Broad catch: TV may be offline, IP wrong, firewall blocking port 8009
        logger.error(
            "Unexpected error connecting to Chromecast at %s: %s",
            config.TV_IP,
            exc,
            exc_info=True,
        )
        return False


def cast_display_page() -> bool:
    """
    Cast the Flask-served display.html page to the TV using DashCast.
    
    DashCast (App ID: 5CB45E5A) is a dedicated web receiver that is
    often more stable for HTML/JS content than the Default Media Receiver.
    """
    global _cast_page_sent

    with _cast_lock:
        cast = _cast

    if cast is None:
        logger.warning("cast_display_page() called but Chromecast is not connected")
        return False

    try:
        url = _build_display_url()
        logger.info("Casting display page to TV via DashCast: %s", url)

        # Before we launch DashCast, record what was running (Netflix, YouTube, etc.)
        global _prev_app_id
        current_app = cast.app_id
        # Ignore DashCast itself or the default Backdrop app
        if current_app and current_app not in ("5CB45E5A", "E8C28D3C", "CC1AD845"):
            _prev_app_id = current_app
            logger.info("Captured previous App ID to restore later: %s", _prev_app_id)
        else:
            _prev_app_id = None

        # Initialize the DashCast controller
        dcast = DashCastController()
        cast.register_handler(dcast)
        
        # Launch DashCast and load our URL
        # force=True ensures it reloads even if DashCast is already open
        dcast.load_url(url, force=True)

        _cast_page_sent = True
        logger.info("DashCast load_url command sent successfully")
        return True

    except Exception as exc:
        logger.error("Failed to cast display page via DashCast: %s", exc, exc_info=True)
        _cast_page_sent = False
        return False


def update_display_text(text: str) -> None:
    """
    Update the text shown on the TV display.

    This does NOT re-cast the page. Instead, it updates the in-memory
    _current_text variable. The display.html page running in the TV's
    browser polls GET /api/cast/current-text every 2 seconds and updates
    the DOM when the text changes.

    This approach avoids the latency of re-casting (which takes 1-3 seconds)
    for every text update.

    Args:
        text: The new text to display on the TV.
    """
    global _current_text

    with _text_lock:
        _current_text = text

    logger.info("Display text updated: %r", text[:80] + "…" if len(text) > 80 else text)


def get_current_text() -> str:
    """
    Return the text currently displayed on the TV.

    Called by the /api/cast/current-text route, which display.html polls.
    Thread-safe.
    """
    with _text_lock:
        return _current_text


def get_connection_status() -> dict:
    """
    Return the current Chromecast connection status.

    Returns a dict suitable for JSON serialisation:
      {
        "online": bool,
        "device_name": str,
        "device_ip": str,
        "model_name": str | None,
      }
    """
    with _cast_lock:
        cast = _cast

    if cast is None:
        return {
            "online": False,
            "device_name": config.TV_NAME,
            "device_ip": config.TV_IP,
            "model_name": None,
        }

    try:
        # is_idle is True when the Cast device is connected but not playing.
        # Accessing cast.status triggers a lightweight status check.
        _ = cast.status
        online = True
    except Exception:
        online = False

    return {
        "online": online,
        "device_name": cast.name,
        "device_ip": config.TV_IP,
        "model_name": cast.model_name,
    }


def disconnect() -> None:
    """
    Gracefully disconnect from the Chromecast and stop monitoring.
    """
    global _cast, _cast_page_sent, _prev_app_id

    with _cast_lock:
        cast = _cast
        _cast = None

    if cast is not None:
        try:
            # Stop packet monitor first since it relies on active session
            from services import packet_monitor
            packet_monitor.stop_monitor()

            # Explicitly stop the current app (DashCast) before disconnecting
            # This returns the TV to its home screen / backdrop
            logger.info("Quitting DashCast on TV...")
            cast.quit_app()

            # Attempt "Best Effort" restoration
            if _prev_app_id:
                logger.info("Attempting to restore previous App: %s", _prev_app_id)
                try:
                    cast.start_app(_prev_app_id)
                    # Give it a moment to trigger the launch before closing socket
                    time.sleep(1)
                except Exception as restore_exc:
                    logger.warning("Restoration failed (likely app requires user): %s", restore_exc)
            
            cast.disconnect(timeout=5)
            _cast_page_sent = False
            _prev_app_id = None
            logger.info("Disconnected from Chromecast")
        except Exception as exc:
            logger.warning("Error during Chromecast disconnect: %s", exc)
