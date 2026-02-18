"""
models.py — SQLAlchemy ORM models for the Text-to-TV Display System.

Tables:
  devices      — known Chromecast/TV devices
  sessions     — connection sessions per device
  messages     — text messages sent to TV
  packet_logs  — network packets captured by Scapy

Relationships:
  Device  1──* Session
  Session 1──* Message
  Session 1──* PacketLog
"""

import logging
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

logger = logging.getLogger(__name__)

# Shared SQLAlchemy instance — imported by app.py and services.
db = SQLAlchemy()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Device
# ---------------------------------------------------------------------------

class Device(db.Model):
    """
    Represents a Chromecast-capable TV device on the local network.

    Phase 1: only one device (hardcoded IP), but the schema supports multiple.
    """

    __tablename__ = "devices"

    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(128), nullable=False)
    ip_address: str = db.Column(db.String(45), nullable=False, unique=True)  # IPv4/IPv6
    mac_address: str = db.Column(db.String(17), nullable=True)               # optional in Phase 1
    last_seen: datetime = db.Column(
        db.DateTime(timezone=True), nullable=True, default=_utcnow
    )
    is_online: bool = db.Column(db.Boolean, nullable=False, default=False)

    # Relationships
    sessions = db.relationship(
        "Session", back_populates="device", cascade="all, delete-orphan", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Device id={self.id} name={self.name!r} ip={self.ip_address} online={self.is_online}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "ip_address": self.ip_address,
            "mac_address": self.mac_address,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "is_online": self.is_online,
        }


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

class Session(db.Model):
    """
    A connection session between the Mac and a TV device.

    connection_type is always 'local' in Phase 1.
    """

    __tablename__ = "sessions"

    id: int = db.Column(db.Integer, primary_key=True)
    device_id: int = db.Column(
        db.Integer, db.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    connection_type: str = db.Column(
        db.String(16),
        nullable=False,
        default="local",
        comment="'local' | 'lan' | 'remote'",
    )
    start_time: datetime = db.Column(
        db.DateTime(timezone=True), nullable=False, default=_utcnow
    )
    end_time: datetime = db.Column(db.DateTime(timezone=True), nullable=True)
    total_messages: int = db.Column(db.Integer, nullable=False, default=0)

    # Relationships
    device = db.relationship("Device", back_populates="sessions")
    messages = db.relationship(
        "Message", back_populates="session", cascade="all, delete-orphan", lazy="dynamic"
    )
    packet_logs = db.relationship(
        "PacketLog", back_populates="session", cascade="all, delete-orphan", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return (
            f"<Session id={self.id} device_id={self.device_id} "
            f"type={self.connection_type!r} msgs={self.total_messages}>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "device_id": self.device_id,
            "connection_type": self.connection_type,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_messages": self.total_messages,
        }


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

class Message(db.Model):
    """
    A single text message sent from the React frontend to the TV.
    """

    __tablename__ = "messages"

    id: int = db.Column(db.Integer, primary_key=True)
    session_id: int = db.Column(
        db.Integer, db.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    text: str = db.Column(db.Text, nullable=False)
    timestamp: datetime = db.Column(
        db.DateTime(timezone=True), nullable=False, default=_utcnow
    )
    delivered: bool = db.Column(db.Boolean, nullable=False, default=False)
    latency_ms: float = db.Column(db.Float, nullable=True)  # round-trip latency in ms

    # Relationships
    session = db.relationship("Session", back_populates="messages")

    def __repr__(self) -> str:
        preview = self.text[:30] + "…" if len(self.text) > 30 else self.text
        return f"<Message id={self.id} delivered={self.delivered} text={preview!r}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "text": self.text,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "delivered": self.delivered,
            "latency_ms": self.latency_ms,
        }


# ---------------------------------------------------------------------------
# PacketLog
# ---------------------------------------------------------------------------

class PacketLog(db.Model):
    """
    A single network packet captured by Scapy between Mac and TV.
    """

    __tablename__ = "packet_logs"

    id: int = db.Column(db.Integer, primary_key=True)
    session_id: int = db.Column(
        db.Integer, db.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    protocol: str = db.Column(db.String(16), nullable=False)   # e.g. 'TCP', 'UDP', 'ICMP'
    source_ip: str = db.Column(db.String(45), nullable=False)
    dest_ip: str = db.Column(db.String(45), nullable=False)
    size_bytes: int = db.Column(db.Integer, nullable=False)
    timestamp: datetime = db.Column(
        db.DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # Relationships
    session = db.relationship("Session", back_populates="packet_logs")

    def __repr__(self) -> str:
        return (
            f"<PacketLog id={self.id} proto={self.protocol} "
            f"{self.source_ip}→{self.dest_ip} {self.size_bytes}B>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "protocol": self.protocol,
            "source_ip": self.source_ip,
            "dest_ip": self.dest_ip,
            "size_bytes": self.size_bytes,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
