# AI Guidance & Collaboration Model

This project was developed using a structured AI collaboration model (**Antigravity**). Per the assessment requirements, this file documents the guidance files and constraints used during development.

## 📋 Prompting Strategy & Constraints
The AI agent was governed by these persistent rules:

1.  **Strict Modularization**: All logic must reside in `services/`, while `routes/` act only as thin interfaces.
2.  **Observability First**: Coding standards forced the inclusion of heartbeat endpoints (`/tv/heartbeat`) and visible debug markers on the TV to avoid "silent failures."
3.  **Maximum Compatibility**: Frontend for the TV receiver must use ES5 JavaScript (`var`, `XMLHttpRequest`) to ensure it works on low-powered integrated TV browsers.

## 🛠️ Guided Decision Making
The AI was used to solve hardware-software hurdles, specifically:
- **DashCast Integration**: Moving from the standard receiver to DashCast for better web page rendering.
- **Private Network Access (PNA)**: Handling local network security headers for TV browsers.
- **State Restoration**: Implementing "best effort" app resumption on disconnect.

## 📁 Collaboration Artifacts
The following files in the `.ai/` directory document the development process:
- `task.md`: Detailed checklist used to maintain state.
- `implementation_plan.md`: Technical blueprints approved before execution.
- `walkthrough.md`: System structure and risk analysis.
