"""
db_service.py — Database operations for the Text-to-TV Display System.

All functions run within a Flask application context (required by SQLAlchemy).
Callers from background threads (e.g. packet_monitor) must push an app context
before calling these functions — see packet_monitor.py for the pattern.

Functions:
  get_or_create_device()  — upsert TV device record
  create_session()        — open a new session
  close_session()         — mark session as ended
  log_message()           — persist a sent text message
  log_packet()            — persist a captured network packet
  get_message_history()   — fetch recent messages (for API)
  get_packet_stats()      — aggregate packet stats (for API)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError

from models import db, Device, Session, Message, PacketLog

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Device
# ---------------------------------------------------------------------------

def get_or_create_device(
    name: str,
    ip_address: str,
    mac_address: Optional[str] = None,
) -> Optional[Device]:
    """
    Upsert a TV device record.

    If a Device with the given ip_address already exists, update its name,
    MAC address, and mark it online. Otherwise create a new record.

    Args:
        name:        Human-readable device name (e.g. "Living Room TV").
        ip_address:  LAN IP of the TV.
        mac_address: Optional MAC/Bluetooth address for the DB record.

    Returns the Device ORM object, or None on DB error.
    """
    try:
        device = Device.query.filter_by(ip_address=ip_address).first()

        if device is None:
            device = Device(
                name=name,
                ip_address=ip_address,
                mac_address=mac_address,
                is_online=True,
                last_seen=_utcnow(),
            )
            db.session.add(device)
            logger.info("Created new device: %s (%s, mac=%s)", name, ip_address, mac_address)
        else:
            device.name = name
            device.is_online = True
            device.last_seen = _utcnow()
            if mac_address:
                device.mac_address = mac_address
            logger.debug("Updated existing device: %s (%s)", name, ip_address)

        db.session.commit()
        return device

    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.error("DB error in get_or_create_device: %s", exc, exc_info=True)
        return None


def mark_device_offline(ip_address: str) -> None:
    """Mark a device as offline (called on disconnect)."""
    try:
        device = Device.query.filter_by(ip_address=ip_address).first()
        if device:
            device.is_online = False
            db.session.commit()
            logger.info("Marked device offline: %s", ip_address)
    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.error("DB error in mark_device_offline: %s", exc, exc_info=True)


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

def create_session(device_id: int, connection_type: str = "local") -> Optional[Session]:
    """
    Open a new connection session for a device.

    Returns the Session ORM object, or None on DB error.
    """
    try:
        session = Session(
            device_id=device_id,
            connection_type=connection_type,
            start_time=_utcnow(),
            total_messages=0,
        )
        db.session.add(session)
        db.session.commit()
        logger.info(
            "Created session id=%d for device_id=%d (type=%s)",
            session.id, device_id, connection_type,
        )
        return session

    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.error("DB error in create_session: %s", exc, exc_info=True)
        return None


def close_session(session_id: int) -> None:
    """
    Mark a session as ended by setting end_time to now.
    """
    try:
        session = Session.query.get(session_id)
        if session:
            session.end_time = _utcnow()
            db.session.commit()
            logger.info("Closed session id=%d", session_id)
    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.error("DB error in close_session: %s", exc, exc_info=True)


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

def log_message(
    session_id: int,
    text: str,
    delivered: bool,
    latency_ms: Optional[float] = None,
) -> Optional[Message]:
    """
    Persist a text message that was sent to the TV.

    Also increments Session.total_messages atomically.

    Returns the Message ORM object, or None on DB error.
    """
    try:
        message = Message(
            session_id=session_id,
            text=text,
            timestamp=_utcnow(),
            delivered=delivered,
            latency_ms=latency_ms,
        )
        db.session.add(message)

        # Increment the session's message counter
        session = Session.query.get(session_id)
        if session:
            session.total_messages += 1

        db.session.commit()
        logger.debug(
            "Logged message id=%d session=%d delivered=%s latency=%.1fms",
            message.id, session_id, delivered, latency_ms or 0,
        )
        return message

    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.error("DB error in log_message: %s", exc, exc_info=True)
        return None


def get_message_history(limit: int = 20) -> list:
    """
    Return the most recent `limit` messages across all sessions, newest first.

    Returns a list of dicts (JSON-serialisable).
    """
    try:
        messages = (
            Message.query
            .order_by(Message.timestamp.desc())
            .limit(limit)
            .all()
        )
        return [m.to_dict() for m in messages]

    except SQLAlchemyError as exc:
        logger.error("DB error in get_message_history: %s", exc, exc_info=True)
        return []


# ---------------------------------------------------------------------------
# PacketLog
# ---------------------------------------------------------------------------

def log_packet(
    session_id: int,
    protocol: str,
    source_ip: str,
    dest_ip: str,
    size_bytes: int,
) -> Optional[PacketLog]:
    """
    Persist a single captured network packet.

    Called from the packet monitor background thread.
    The caller is responsible for pushing a Flask app context before calling.

    Returns the PacketLog ORM object, or None on DB error.
    """
    try:
        pkt_log = PacketLog(
            session_id=session_id,
            protocol=protocol,
            source_ip=source_ip,
            dest_ip=dest_ip,
            size_bytes=size_bytes,
            timestamp=_utcnow(),
        )
        db.session.add(pkt_log)
        db.session.commit()
        return pkt_log

    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.error("DB error in log_packet: %s", exc, exc_info=True)
        return None


def get_packet_stats(session_id: Optional[int] = None, limit: int = 20) -> dict:
    """
    Return aggregate packet statistics.

    Args:
        session_id: If provided, filter to a specific session.
        limit:      Number of recent packets to include in the live list.

    Returns a dict:
      {
        "total_packets": int,
        "total_bytes": int,
        "protocol_breakdown": {"TCP": int, "UDP": int, ...},
        "recent_packets": [ {...}, ... ]   # newest first
      }
    """
    try:
        query = PacketLog.query
        if session_id is not None:
            query = query.filter_by(session_id=session_id)

        all_packets = query.all()

        total_packets = len(all_packets)
        total_bytes = sum(p.size_bytes for p in all_packets)

        # Protocol breakdown
        breakdown: dict = {}
        for p in all_packets:
            breakdown[p.protocol] = breakdown.get(p.protocol, 0) + 1

        # Recent packets (newest first)
        recent = (
            query.order_by(PacketLog.timestamp.desc())
            .limit(limit)
            .all()
        )

        return {
            "total_packets": total_packets,
            "total_bytes": total_bytes,
            "protocol_breakdown": breakdown,
            "recent_packets": [p.to_dict() for p in recent],
        }

    except SQLAlchemyError as exc:
        logger.error("DB error in get_packet_stats: %s", exc, exc_info=True)
        return {
            "total_packets": 0,
            "total_bytes": 0,
            "protocol_breakdown": {},
            "recent_packets": [],
        }
