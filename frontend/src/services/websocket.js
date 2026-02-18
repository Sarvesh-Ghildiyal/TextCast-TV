/**
 * websocket.js — Socket.IO client for real-time packet updates.
 *
 * Connects to the Flask-SocketIO server at localhost:5000.
 * Exports a helper to subscribe to 'packet_update' events.
 */

import { io } from 'socket.io-client';

// Single shared socket instance — created once, reused across components.
const socket = io('http://localhost:5001', {
    autoConnect: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 2000,
    transports: ['websocket', 'polling'],
});

socket.on('connect', () => {
    console.log('[SocketIO] Connected:', socket.id);
});

socket.on('disconnect', (reason) => {
    console.log('[SocketIO] Disconnected:', reason);
});

socket.on('connect_error', (err) => {
    console.warn('[SocketIO] Connection error:', err.message);
});

/**
 * Subscribe to real-time packet updates from the backend.
 *
 * @param {function} callback - Called with each packet_update payload:
 *   { protocol, source_ip, dest_ip, size_bytes, session_id, timestamp }
 * @returns {function} Unsubscribe function — call it in useEffect cleanup.
 */
export const onPacketUpdate = (callback) => {
    socket.on('packet_update', callback);
    return () => socket.off('packet_update', callback);
};

export default socket;
