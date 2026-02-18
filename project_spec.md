Rules for Agent:
- Do not modify stack
- Do not skip error handling
- Use proper logging
- Use async-safe background threading
- Ensure Mac M1 compatibility
- Do not invent services outside architecture


COMPLETE PROMPT FOR PROJECT

PROJECT: Text-to-TV Display System using PyChromecast

I need you to help me build a complete application with the following requirements:

Project Goal: Create a system where I can type text on my Mac M1 Air and it displays on my Android TV in real-time, leveraging the TV's existing built-in Chromecast receiver (no app installation on TV needed). The system should log all activities to a relational database and provide network packet monitoring.

Core Architecture:

React Frontend (Mac) ←→ Flask Backend (Mac) → PyChromecast → Android TV (Built-in Cast)
                              ↓
                        PostgreSQL Database
                              ↓
                        Scapy (Packet Monitor)
Technical Stack (MANDATORY):

Frontend: React (runs on Mac)
Backend: Flask with Python 3.x (runs on Mac)
Casting: PyChromecast library (to communicate with Android TV's built-in Chromecast)
Database: PostgreSQL with SQLAlchemy ORM
Packet Monitoring: Scapy
Real-time Updates: Flask-SocketIO (WebSocket between React and Flask)
Implementation Phases (Current Focus: Phase 1):

Phase 1 (NOW): Local network with hardcoded IPs - Mac and TV on same WiFi
Phase 2 (FUTURE): Same WiFi with device discovery (mDNS)
Phase 3 (FUTURE): Remote access over internet
Core Features Required:

Text Display System:
React frontend: Simple text input field and "Send to TV" button
User types text → Sends to Flask backend via HTTP/WebSocket
Flask backend receives text → Uses PyChromecast to display on TV
TV displays text fullscreen using its built-in Cast receiver
Flask serves a simple HTML page that shows the text (PyChromecast casts this page to TV)
Database Schema (PostgreSQL + SQLAlchemy): Must track:
Devices table: TV info (name, IP address, MAC address, last_seen timestamp, is_online boolean)
Sessions table: Connection sessions (device_id FK, start_time, end_time, connection_type: 'local'/'lan'/'remote')
Messages table: All text sent (session_id FK, text content, timestamp, delivery_status, latency_ms)
Packet_logs table: Network packets (session_id FK, protocol, source_ip, dest_ip, packet_size_bytes, timestamp)
Packet Monitoring:
Use Scapy to capture network packets related to the Cast communication
Filter only relevant packets (between Mac and TV)
Store packet data in database
Display packet statistics in React frontend (real-time updates via WebSocket)
Configuration:
Hardcoded TV IP address for Phase 1 (e.g., "192.168.1.100")
Hardcoded TV name (e.g., "Living Room TV")
Store these in a config.py file for easy updates
Project Structure I Want:

text-to-tv-cast/
├── backend/
│   ├── app.py                    # Main Flask application
│   ├── config.py                 # Configuration (hardcoded IPs, DB connection)
│   ├── models.py                 # SQLAlchemy models (Device, Session, Message, PacketLog)
│   ├── requirements.txt          # Python dependencies
│   ├── services/
│   │   ├── cast_service.py       # PyChromecast logic for TV communication
│   │   ├── packet_monitor.py    # Scapy packet capture logic
│   │   └── db_service.py         # Database operations
│   ├── routes/
│   │   ├── cast_routes.py        # API endpoints for casting
│   │   └── monitor_routes.py    # API endpoints for packet stats
│   └── templates/
│       └── display.html          # HTML template for TV display
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── TextInput.jsx           # Main text input component
│   │   │   ├── ConnectionStatus.jsx    # Shows TV connection status
│   │   │   ├── PacketMonitor.jsx       # Displays packet statistics
│   │   │   └── MessageHistory.jsx      # Shows sent message history
│   │   ├── services/
│   │   │   ├── api.js                  # Axios HTTP client for Flask API
│   │   │   └── websocket.js            # Socket.IO client for real-time updates
│   │   ├── App.jsx
│   │   └── App.css
│   ├── package.json
│   └── README.md
│
└── README.md                     # Setup instructions
Detailed Implementation Requirements:

1. Backend - Flask (app.py):

python
# Should include:
- Flask app with CORS enabled
- Flask-SocketIO for WebSocket support
- SQLAlchemy database initialization
- Routes for:
  * POST /api/cast/send - Send text to TV
  * GET /api/cast/status - Check TV connection status
  * GET /api/messages/history - Get message history from DB
  * GET /api/packets/stats - Get packet statistics
  * WebSocket event: 'packet_update' - Real-time packet data
- PyChromecast integration to:
  * Connect to TV using hardcoded IP
  * Cast the Flask-served HTML page to TV
  * Update the displayed text dynamically
2. Backend - Cast Service (cast_service.py):

python
# Should include:
- Function to initialize PyChromecast with hardcoded TV IP
- Function to cast HTML page to TV
- Function to update displayed text (refresh the page or use custom receiver)
- Error handling for TV offline/unreachable
- Log all cast operations to database
3. Backend - Display Template (templates/display.html):

html
# Simple HTML page that:
- Shows text in large font (10vw font-size)
- Black background, white text
- Centered on screen
- Auto-refreshes every 2 seconds to check for new text
- OR uses JavaScript to poll Flask API for text updates
4. Backend - Models (models.py):

python
# SQLAlchemy models with proper relationships:
- Device model (id, name, ip_address, mac_address, last_seen, is_online)
- Session model (id, device_id FK, connection_type, start_time, end_time, total_messages)
- Message model (id, session_id FK, text, timestamp, delivered, latency_ms)
- PacketLog model (id, session_id FK, protocol, source_ip, dest_ip, size_bytes, timestamp)
5. Backend - Packet Monitor (packet_monitor.py):

python
# Scapy integration:
- Capture packets on the network interface
- Filter packets between Mac and TV (use hardcoded IPs)
- Extract: protocol, packet size, source/dest IPs, timestamp
- Store in database asynchronously
- Emit packet data via WebSocket to frontend
- Run in separate thread to avoid blocking Flask
6. Frontend - React App:

jsx
// Main features:
- Text input area with "Send to TV" button
- Connection status indicator (green if TV reachable, red if not)
- Message history list (fetched from Flask API)
- Real-time packet monitor dashboard showing:
  * Total packets sent/received
  * Average latency
  * Protocol breakdown (TCP, UDP, etc.)
  * Live packet list (last 20 packets)
- Use Socket.IO client to receive real-time packet updates
- Use Axios for API calls
- Simple, clean UI (can use basic CSS or Tailwind)
7. Configuration (config.py):

python
# Should contain:
- TV_IP = "192.168.1.100"  # Hardcoded for Phase 1
- TV_NAME = "Living Room TV"
- SQLALCHEMY_DATABASE_URI = "postgresql://user:password@localhost/textcast_db"
- FLASK_PORT = 5000
- REACT_DEV_PORT = 3000
```

**Dependencies to Include:**

**Backend (requirements.txt):**
```
Flask==3.0.0
Flask-SocketIO==5.3.5
Flask-SQLAlchemy==3.1.1
Flask-CORS==4.0.0
Flask-Migrate==4.0.5
PyChromecast==13.0.8
scapy==2.5.0
psycopg2-binary==2.9.9
python-socketio==5.10.0
eventlet==0.33.3
Frontend (package.json dependencies):

json
{
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "axios": "^1.6.0",
  "socket.io-client": "^4.7.0"
}
What I Need From You:

✅ Complete working code for all files mentioned above
✅ Database schema with proper SQLAlchemy relationships and migrations setup
✅ PyChromecast implementation that:
Connects to TV using hardcoded IP
Serves and casts an HTML page to display text
Updates text dynamically
✅ Scapy integration that captures and filters relevant packets
✅ Flask-SocketIO setup for real-time packet monitoring updates
✅ React components with clean UI and real-time updates
✅ Complete setup instructions including:
PostgreSQL database creation commands
How to run database migrations
How to start Flask backend
How to start React frontend
How to find your Mac's local IP address
How to test the casting functionality
✅ Error handling throughout (TV unreachable, DB connection failures, etc.)
✅ Comments explaining complex parts, especially:
PyChromecast usage
Scapy packet filtering
WebSocket event handling
Additional Context:

I'm a CSE graduate, comfortable with programming
I know React and Flask basics
Need to learn: SQLAlchemy ORM, PyChromecast library, Scapy packet capture
Mac M1 Air running macOS
Android TV on local network (hardcoded IP for now)
TV has Chromecast built-in (no app installation needed)
Success Criteria: When complete, I should be able to:

Start the Flask backend
Start the React frontend
Type text in the React UI
Click "Send to TV"
See the text appear on my Android TV screen within 2-3 seconds
View packet statistics in real-time
Check message history in the database
See all operations logged to PostgreSQL
Please provide production-ready code with proper error handling, logging, and clear documentation. Include step-by-step setup instructions for a beginner-friendly experience.

END OF PROMPT