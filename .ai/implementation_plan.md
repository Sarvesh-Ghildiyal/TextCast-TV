# Implementation Plan - Disconnect API and Display Debugging

This plan adds a disconnect API and user interface button to allow users to gracefully stop the casting session. It also includes steps to debug why the TV is stuck on the Chromecast logo.

## Proposed Changes

### Backend

#### [MODIFY] [cast_service.py](file:///Users/sarvesh/Development/better/assessment/backend/services/cast_service.py)
- Update `disconnect()` to also call `packet_monitor.stop_monitor()` to ensure all monitoring stops when the user disconnects.

#### [MODIFY] [cast_routes.py](file:///Users/sarvesh/Development/better/assessment/backend/routes/cast_routes.py)
- Add `POST /api/cast/disconnect` endpoint that calls `cast_service.disconnect()`.

### Frontend

#### [MODIFY] [api.js](file:///Users/sarvesh/Development/better/assessment/frontend/src/services/api.js)
- Add `disconnect()` to the API service.

#### [MODIFY] [ConnectionStatus.jsx](file:///Users/sarvesh/Development/better/assessment/frontend/src/components/ConnectionStatus.jsx)
- Add a "Disconnect" button shown when `status.online` is true.

## TV Display Debugging (Logo Issue)

We will implement a heartbeat endpoint and absolute URL resolution to identify why the TV browser isn't executing the polling logic.

### Deep Debug Steps
1. **[NEW] [Heartbeat Route]**: Add `GET /api/tv/heartbeat` to track when the TV's JavaScript successfully starts.
2. **[Absolute URLs]**: Change `display.html` to use absolute URLs for all API calls.
3. **[On-Screen Logs]**: Add high-visibility debug markers (red/green dots) to the TV screen to show JS status.

## UX Improvement: State Restoration on Disconnect

We will implement a "Best Effort" restoration to return the TV to its previous application (e.g., Netflix, YouTube) instead of the generic home screen.

### Technical Constraints (DRM/Privacy)
While we can detect the running **App ID** (e.g., Netflix), most premium apps hide the specific **Content ID** and **Playback Position** from local network listeners for security. Therefore, we can return the TV to the previous *app*, but the user may need to re-select their profile/movie manually.

### Steps
1. **[Capture]**: In `init_chromecast()`, capture the current `app_id` before launching DashCast.
2. **[Store]**: Save this `_prev_app_id` in the module's state.
3. **[Restore]**: In `disconnect()`, if `_prev_app_id` exists and isn't DashCast or the setup app, call `cast.start_app(_prev_app_id)` before closing the connection.


### Manual Verification
1. Start backend: `sudo python3 app.py`
2. Start frontend: `npm run dev -- --port 3000`
3. Click **Connect** in the UI.
4. Verify the TV shows the display page (or debug if stuck).
5. Click **Disconnect** in the UI.
6. Verify the TV exits the cast and the UI updates to "Offline".
7. Verify the `sudo` terminal shows "Disconnected from Chromecast" and packet monitor stopping.

### Automated Tests
- None planned for this phase.
