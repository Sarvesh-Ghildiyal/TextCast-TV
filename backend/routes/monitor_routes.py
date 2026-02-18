"""
monitor_routes.py — API endpoints for packet monitoring statistics.

Routes:
  GET /api/packets/stats — aggregate packet statistics from DB

All routes return JSON only.
"""

import logging

from flask import Blueprint, jsonify, request

from services import db_service

logger = logging.getLogger(__name__)

monitor_bp = Blueprint("monitor", __name__)


@monitor_bp.get("/packets/stats")
def packet_stats():
    """
    Return aggregate packet statistics.

    Optionally filter by session_id. Returns total counts, protocol breakdown,
    and a live list of the most recent packets.

    Query params:
      session_id (int, optional) — filter to a specific session
      limit      (int, default 20, max 100) — number of recent packets to return

    Response 200 (JSON):
      {
        "total_packets": 42,
        "total_bytes": 18432,
        "protocol_breakdown": {
          "TCP": 30,
          "UDP": 12
        },
        "recent_packets": [
          {
            "id": 42,
            "session_id": 1,
            "protocol": "TCP",
            "source_ip": "192.168.1.10",
            "dest_ip": "192.168.1.100",
            "size_bytes": 512,
            "timestamp": "2026-02-18T14:30:00+00:00"
          },
          ...
        ]
      }

    Response 400 (JSON):
      { "error": "Invalid parameter" }

    Response 500 (JSON):
      { "error": "Could not fetch packet statistics" }
    """
    # --- Parse query params ------------------------------------------------
    session_id = None
    raw_session = request.args.get("session_id")
    if raw_session is not None:
        try:
            session_id = int(raw_session)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid 'session_id' — must be an integer"}), 400

    try:
        limit = int(request.args.get("limit", 20))
        limit = max(1, min(limit, 100))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid 'limit' — must be an integer"}), 400

    # --- Fetch stats -------------------------------------------------------
    try:
        stats = db_service.get_packet_stats(session_id=session_id, limit=limit)
        return jsonify(stats)
    except Exception as exc:
        logger.error("Error fetching packet stats: %s", exc, exc_info=True)
        return jsonify({
            "error": "Could not fetch packet statistics",
            "total_packets": 0,
            "total_bytes": 0,
            "protocol_breakdown": {},
            "recent_packets": [],
        }), 500
