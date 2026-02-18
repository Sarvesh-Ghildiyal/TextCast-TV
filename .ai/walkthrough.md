# Assessment Walkthrough: Text-to-TV Display System

**Candidate**: Sarvesh Ghildiyal  
**Project**: Real-time Text-to-TV Casting with Packet Monitoring

---

## 🏗️ System Structure & Logical Organization

The system follows a clean "Service-Component" architecture to ensure clear boundaries and change resilience.

- **Backend (Flask)**:
  - `routes/`: Handles HTTP/WebSocket interfaces (CORS, JSON validation).
  - `services/`: Encapsulates business logic (PyChromecast, Scapy, DB interactions).
  - `models/`: Centralized SQLAlchemy models for schema enforcement.
- **Frontend (React)**:
  - `components/`: Modular UI (TextInput, PacketMonitor, ConnectionStatus).
  - `services/`: API and WebSocket abstractions using Axios and Socket.IO.

---

## 🤖 AI Usage & Guidance

This project was developed in a pair-programming session with **Antigravity**. The AI was guided by structured artifacts:

1.  **task.md**: A live checklist used to track progress and state.
2.  **implementation_plan.md**: Technical blueprints reviewed and approved before execution.
3.  **Strict Constraints**: The AI was restricted from inventing services outside the architecture and forced to use proper logging and error handling.

### Key AI Contributions:
- **Debugging**: Identified a `TypeError` caused by a breaking change in PyChromecast v13.x return types.
- **Problem Solving**: When the TV was stuck on the loading logo, the AI proposed a "Roundabout" using **DashCast** and **Private Network Access headers**.
- **Refactoring**: Safely migrated the database from PostgreSQL to MySQL without breaking existing API contracts.

---

## 🛑 Risks & Mitigation

| Risk | Mitigation |
| :--- | :--- |
| **Network Isolation** | Added `Access-Control-Allow-Private-Network` headers to allow TV-to-Mac communication. |
| **TV Compatibility** | Switched from `Default Media Receiver` to `DashCast` for more robust web page rendering. |
| **Data Integrity** | Implemented SQLAlchemy schema constraints and Flask JSON validation on all inputs. |

---

## 🚀 Extension Approach

If given more time (Phase 2 & 3), the system would evolve as follows:

1.  **mDNS Discovery**: Replace hardcoded IPs with `pychromecast.discovery` to auto-detect TVs on the network.
2.  **Cloud Relay**: Implement a signaling server (Turn/Stun) to allow casting from a phone to a TV even if they are NOT on the same WiFi.
3.  **Advanced Monitoring**: Expand Scapy capture to analyze latencies per packet and detect network congestion.

---

## 📽️ Proof of Work

The system has been verified manually:
- **API**: `POST /api/cast/disconnect` confirmed via local curl tests.
- **UI**: Connection Status card accurately reflects the PyChromecast socket state.
- **Visuals**: A live clock on the TV ensures the user knows the display is active and "ticking."
- **Seamless Experience**: Implemented "Best Effort" state restoration — the system records the active TV app (e.g., Netflix) and attempts to re-launch it upon disconnection.

---
*Developed for the Better Software Associate Software Engineer Assessment.*
