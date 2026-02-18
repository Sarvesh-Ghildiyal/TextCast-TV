# Text-to-TV Display System

A real-time text casting system built for the Better Software Associate Software Engineer Assessment. This system allows you to send text from a Mac app to an Android TV's built-in Chromecast receiver, with real-time network packet monitoring.

## 📺 Project Overview

The application consists of a **React Frontend** for control, a **Flask Backend** for orchestration, and leverages **PyChromecast** to communicate with the TV. It includes a custom packet monitor using **Scapy** to visualize network traffic between the Mac and the TV.

---

## 🚀 Key Technical Decisions

### 1. DashCast for Web Rendering
Initially, the project used the "Default Media Receiver." However, modern TVs often have strict security (Private Network Access) that prevents simple HTML pages from polling a local API.
**Decision**: Swapped to **DashCast (App ID: 5CB45E5A)**. DashCast is a robust, dedicated web receiver that handles arbitrary URLs more reliably than standard media players.

### 2. MySQL Persistence
Migrated from PostgreSQL to **MySQL** using the `PyMySQL` driver.
**Decision**: MySQL was chosen for its ubiquity and lightweight setup on macOS via Homebrew, ensuring the system is "Change Resilient" by demonstrating a smooth database migration early in development.

### 3. Observability & Debugging (Heartbeat System)
Debugging a remote TV browser is difficult.
**Decision**: Implemented a **Heartbeat + Debug Marker** system. The TV's JavaScript signals the backend as soon as it executes, and visual dots (Green/Blue) on the TV screen indicate the connection status. This solves the "Black Box" problem of TV casting.

### 4. Best Effort State Restoration
When casting concludes, DashCast is quit, and the system attempts to re-launch the previously active application (e.g., Netflix, YouTube).
**Decision**: This provides a premium "seamless" UX by returning the user to where they were before the interruption, within technical limitations.

### 5. Direct IP vs mDNS (Phase 1)
**Decision**: For Phase 1, we used **Direct IP connections**. This bypasses flaky mDNS discovery on complex WiFi networks and ensures 100% connection reliability while the environment is being established.

---

## 🛠️ Technical Stack

- **Frontend**: React (Vite) + Axios + Socket.IO-client
- **Backend**: Python 3.9 + Flask + Flask-SocketIO
- **Database**: MySQL (SQLAlchemy ORM)
- **Networking**: PyChromecast (v13.x) + Scapy (Network Sniffing)

---

## 🔧 Setup & Installation

### 1. Prerequisites
- Python 3.9+
- Node.js & npm
- MySQL Server (Running on localhost)
- TV with Chromecast built-in

### 2. Backend Setup
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Update config.py with your TV_IP
flask db upgrade
sudo python3 app.py  # sudo required for Scapy packet sniffing
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev -- --port 3000
```

---

## 🤝 AI Collaboration
This project was built using **Antigravity (Google DeepMind)**. The AI was used for architectural planning, debugging PyChromecast API versioning mismatches, and implementing the Scapy packet capture logic. 
*Detailed AI guidance files are located in the `.gemini/brain/` directory.*
