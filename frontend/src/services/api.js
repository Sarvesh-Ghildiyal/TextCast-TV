/**
 * api.js — Axios HTTP client for the Flask backend.
 *
 * All API calls go through this module. The base URL is hardcoded to
 * localhost:5000 for Phase 1 (same-machine development).
 */

import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:5001',
    timeout: 10000,
    headers: { 'Content-Type': 'application/json' },
});

/**
 * Send text to the TV.
 * @param {string} text
 * @returns {Promise<{success: boolean, latency_ms: number, message_id: number|null}>}
 */
export const sendText = (text) =>
    api.post('/api/cast/send', { text }).then((r) => r.data);

/**
 * Get TV connection status.
 * @returns {Promise<{online: boolean, device_name: string, device_ip: string}>}
 */
export const getStatus = () =>
    api.get('/api/cast/status').then((r) => r.data);

/**
 * Disconnect from the TV.
 * @returns {Promise<{success: boolean, message: string}>}
 */
export const disconnectFromTV = () =>
    api.post('/api/cast/disconnect').then((r) => r.data);

/**
 * Get message history.
 * @param {number} [limit=20]
 * @returns {Promise<{messages: Array, count: number}>}
 */
export const getHistory = (limit = 20) =>
    api.get('/api/messages/history', { params: { limit } }).then((r) => r.data);

/**
 * Get packet statistics.
 * @returns {Promise<{total_packets: number, protocol_breakdown: object, recent_packets: Array}>}
 */
export const getPacketStats = () =>
    api.get('/api/packets/stats').then((r) => r.data);

export default api;
