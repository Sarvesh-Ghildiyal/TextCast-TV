"""
packet_monitor.py — Scapy network packet capture for the Text-to-TV Display System.

═══════════════════════════════════════════════════════════════════════════════
HOW THE BPF FILTER WORKS
═══════════════════════════════════════════════════════════════════════════════
BPF (Berkeley Packet Filter) is a kernel-level packet filtering language.
Scapy passes the BPF expression to the OS kernel, which applies it in-kernel
BEFORE packets are copied to userspace. This is far more efficient than
capturing everything and filtering in Python.

Our filter:
    "host <TV_IP>"

This matches any packet where EITHER the source OR destination IP equals TV_IP.
On macOS, this is equivalent to:
    "src host <TV_IP> or dst host <TV_IP>"

Why not filter by both Mac IP and TV IP?
  "host <MAC_IP> and host <TV_IP>" would match packets where BOTH src and dst
  are those IPs simultaneously — which is impossible for a single packet.
  The correct bidirectional filter is:
    "(src host <MAC_IP> and dst host <TV_IP>) or (src host <TV_IP> and dst host <MAC_IP>)"
  We simplify to "host <TV_IP>" since all relevant packets involve the TV.

═══════════════════════════════════════════════════════════════════════════════
HOW THREADING IS HANDLED SAFELY
═══════════════════════════════════════════════════════════════════════════════
Scapy's sniff() is a blocking call — it runs forever until stopped.
We run it in a daemon thread so it doesn't block Flask's main thread.

Thread lifecycle:
  1. start_monitor(session_id, app) — creates and starts a daemon thread
  2. Thread runs _capture_loop() which calls scapy.sniff(prn=_handle_packet, ...)
  3. stop_monitor() sets _stop_event, which sniff() checks via stop_filter=

Stop mechanism:
  scapy.sniff() accepts a stop_filter= callable. We pass a function that checks
  threading.Event.is_set(). When stop_monitor() sets the event, the next packet
  (or timeout) causes sniff() to return, ending the loop cleanly.

  We also set a store=False flag so Scapy doesn't accumulate packets in memory.

Flask app context in background thread:
  SQLAlchemy requires a Flask application context to use db.session.
  Background threads don't have one by default. We push one explicitly:
    with app.app_context():
        db_service.log_packet(...)
  The `app` object is passed to start_monitor() and stored in the thread closure.

SocketIO emission from background thread:
  Flask-SocketIO's socketio.emit() is NOT thread-safe by default.
  We use socketio.emit() with the `namespace='/'` argument from the background
  thread. With eventlet async_mode, this is safe because eventlet's monkey-patch
  makes threading cooperative — the emit is queued into the eventlet hub.

Scapy on macOS requires root/sudo:
  Raw socket capture requires elevated privileges on macOS.
  Run the Flask server with: sudo python app.py
  Or grant the Python binary raw socket access via:
    sudo setcap cap_net_raw+eip $(which python3)  ← Linux only
  On macOS, sudo is the simplest approach.
"""

import logging
import threading
import time
from typing import Optional

from flask import Flask

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_stop_event = threading.Event()
_monitor_thread: Optional[threading.Thread] = None
_current_session_id: Optional[int] = None
_app: Optional[Flask] = None          # Flask app reference for app context
_socketio = None                       # Flask-SocketIO instance (injected at startup)

# Each start_monitor() creates a fresh Event and stores it here so
# stop_monitor() can signal the correct thread without a race against
# Flask's debug-mode reloader creating a new module-level event.
_stop_event: Optional[threading.Event] = None

# Lock protecting the above mutable state
_state_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def set_socketio(sio) -> None:
    """
    Inject the Flask-SocketIO instance.

    Called once from app.py after socketio is initialised.
    Required so the background thread can emit WebSocket events.
    """
    global _socketio
    _socketio = sio
    logger.debug("packet_monitor: SocketIO instance registered")


def start_monitor(session_id: int, app: Flask) -> bool:
    """
    Start the Scapy packet capture in a background daemon thread.

    Args:
        session_id: The active DB session ID to associate packets with.
        app:        The Flask application instance (for app context in thread).

    Returns:
        True if the thread started, False if already running or Scapy unavailable.
    """
    global _monitor_thread, _current_session_id, _app, _stop_event

    with _state_lock:
        if _monitor_thread is not None and _monitor_thread.is_alive():
            logger.warning("Packet monitor already running — ignoring start request")
            return False

        # Create a FRESH stop event for this capture session.
        # This avoids a race where Flask's debug reloader sets the old module-level
        # event just as a new thread is starting.
        stop_event = threading.Event()
        _stop_event = stop_event
        _current_session_id = session_id
        _app = app

        # daemon=True: thread dies automatically when the main process exits
        _monitor_thread = threading.Thread(
            target=_capture_loop,
            args=(session_id, app, stop_event),
            name="packet-monitor",
            daemon=True,
        )
        _monitor_thread.start()
        logger.info(
            "Packet monitor started (session_id=%d, TV_IP=%s)",
            session_id, config.TV_IP,
        )
        return True


def stop_monitor(timeout: float = 5.0) -> None:
    """
    Signal the capture thread to stop and wait for it to exit.
    """
    global _monitor_thread, _stop_event

    with _state_lock:
        thread = _monitor_thread
        event = _stop_event

    if thread is None or not thread.is_alive():
        logger.debug("Packet monitor not running — nothing to stop")
        return

    logger.info("Stopping packet monitor...")
    if event is not None:
        event.set()
    thread.join(timeout=timeout)

    if thread.is_alive():
        logger.warning("Packet monitor thread did not stop within %.1fs", timeout)
    else:
        logger.info("Packet monitor stopped cleanly")

    with _state_lock:
        _monitor_thread = None


def is_running() -> bool:
    """Return True if the capture thread is alive."""
    with _state_lock:
        return _monitor_thread is not None and _monitor_thread.is_alive()


# ---------------------------------------------------------------------------
# Internal — capture loop
# ---------------------------------------------------------------------------

def _capture_loop(session_id: int, app: Flask, stop_event: threading.Event) -> None:
    """
    Entry point for the background capture thread.

    Runs scapy.sniff() in a loop. If sniff() exits unexpectedly (e.g. due to
    a transient error), we wait 2 seconds and retry — unless stop_event is set.
    """
    try:
        from scapy.all import sniff  # deferred import — scapy is slow to import
    except ImportError:
        logger.error(
            "Scapy is not installed. Install it with: pip install scapy"
        )
        return

    # BPF filter: capture only packets involving the TV's IP address.
    bpf_filter = f"host {config.TV_IP}"
    logger.info("Packet capture BPF filter: %r", bpf_filter)

    while not stop_event.is_set():
        try:
            logger.debug("Starting scapy.sniff() with filter=%r", bpf_filter)
            sniff(
                filter=bpf_filter,
                prn=lambda pkt: _handle_packet(pkt, session_id, app),
                store=False,
                stop_filter=lambda _: stop_event.is_set(),
                timeout=1,
            )
        except PermissionError:
            logger.error(
                "Scapy requires root privileges to capture packets on macOS. "
                "Run the server with: sudo python app.py"
            )
            break
        except Exception as exc:
            if stop_event.is_set():
                break
            logger.error("Scapy sniff error: %s — retrying in 2s", exc, exc_info=True)
            time.sleep(2)

    logger.info("Packet capture loop exited")


def _handle_packet(packet, session_id: int, app: Flask) -> None:
    """
    Callback invoked by Scapy for each captured packet.

    Extracts protocol, IPs, and size, then:
      1. Persists to DB (within a Flask app context)
      2. Emits a WebSocket 'packet_update' event to all connected clients

    This function runs in the background thread — NOT in a Flask request context.
    We push an app context explicitly for the DB write.
    """
    try:
        from scapy.layers.inet import IP, TCP, UDP, ICMP  # deferred import

        # Only process IP packets (ignore ARP, etc.)
        if not packet.haslayer(IP):
            return

        ip_layer = packet[IP]
        source_ip: str = ip_layer.src
        dest_ip: str = ip_layer.dst
        size_bytes: int = len(packet)

        # Determine protocol name
        if packet.haslayer(TCP):
            protocol = "TCP"
        elif packet.haslayer(UDP):
            protocol = "UDP"
        elif packet.haslayer(ICMP):
            protocol = "ICMP"
        else:
            protocol = str(ip_layer.proto)  # numeric fallback (e.g. "47" for GRE)

        logger.debug(
            "Packet: %s %s → %s (%d bytes)",
            protocol, source_ip, dest_ip, size_bytes,
        )

        # Build the payload for the WebSocket event
        packet_data = {
            "protocol": protocol,
            "source_ip": source_ip,
            "dest_ip": dest_ip,
            "size_bytes": size_bytes,
            "session_id": session_id,
            "timestamp": time.time(),
        }

        # --- DB write (requires Flask app context) -------------------------
        # Background threads don't have an app context automatically.
        # We push one here so SQLAlchemy's db.session works correctly.
        try:
            with app.app_context():
                from services import db_service
                db_service.log_packet(
                    session_id=session_id,
                    protocol=protocol,
                    source_ip=source_ip,
                    dest_ip=dest_ip,
                    size_bytes=size_bytes,
                )
        except Exception as db_exc:
            # DB errors must not crash the capture thread
            logger.error("Failed to log packet to DB: %s", db_exc)

        # --- WebSocket emit ------------------------------------------------
        # Emit 'packet_update' to all connected Socket.IO clients.
        # With eventlet async_mode, this is safe from a background thread.
        if _socketio is not None:
            try:
                _socketio.emit("packet_update", packet_data, namespace="/")
            except Exception as sio_exc:
                logger.error("Failed to emit packet_update: %s", sio_exc)

    except Exception as exc:
        # Broad catch: packet parsing errors must not crash the capture thread
        logger.error("Error handling packet: %s", exc, exc_info=True)
