"""
wsgi.py — Production WSGI entry point.

Use this file when running behind a production WSGI server (e.g. gunicorn).
eventlet.monkey_patch() MUST be called here, before importing the Flask app,
so that all stdlib sockets/threads are cooperative.

Usage (development):
    python app.py

Usage (production with gunicorn + eventlet worker):
    gunicorn --worker-class eventlet -w 1 wsgi:application
"""

import eventlet

# Monkey-patch MUST be the very first thing — before any other import
# that touches sockets, threading, or ssl.
eventlet.monkey_patch()

from app import app, socketio  # noqa: E402

# gunicorn / other WSGI servers look for a callable named `application`
application = app
