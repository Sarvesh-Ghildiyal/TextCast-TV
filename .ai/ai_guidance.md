# AI Guidance & Collaboration Model

This document outlines how AI (Antigravity) was guided and constrained during the development of this project.

## 📋 Guidance Framework

The project followed a strictly governed AGENTIC workflow:

1.  **Context Injection**: The AI was provided with a persistent context of the codebase and project history at the start of every phase.
2.  **Task Decomposition**: Every objective was broken down into granular items in `brain/task.md`.
3.  **Formal Planning**: No code was executed without a reviewed `implementation_plan.md`. This ensured that architectural decisions (like switching to MySQL) were deliberate and not hallucinatory.
4.  **Verification Loops**: Every change was followed by a verification phase (logs, curl tests, UI checks).

## 🧩 Collaboration Patterns

### 1. Planning Mode (Design)
- The user provided the `project_spec.md` as the "Source of Truth".
- The AI generated implementation plans for Approval.
- Example: Planning the `GET /api/packets/stats` endpoint before writing the Scapy logic.

### 2. Execution Mode (Coding)
- The AI performed file edits using structured tool calls (`replace_file_content`, `multi_replace_file_content`).
- Strict linting and syntax checks were enforced to prevent breaking the build.

### 3. Verification Mode (Debugging)
- When the TV failed to load the display, the AI switched to a "Deep Debug" status.
- It proactively implemented heartbeat routes and visbile on-screen markers to bridge the "black box" gap between the Mac and the TV.

## 📂 Guidance Files
The following files (found in `.gemini/brain/`) constitute the full "Hiring Team Review" for AI guidance:
- `task.md`: Development roadmap and status.
- `implementation_plan.md`: Design docs and technical rationale.
- `walkthrough.md`: Proof of work and architectural summary.

---
*This file is part of the Better Software Associate Software Engineer Assessment.*
