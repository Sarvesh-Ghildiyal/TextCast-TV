/**
 * MessageHistory.jsx
 *
 * Fetches and displays the last 20 messages sent to the TV.
 * Refreshes automatically when a new message is sent (via the `refresh` prop).
 */

import { useEffect, useState } from 'react';
import { getHistory } from '../services/api';

function formatTime(isoString) {
    if (!isoString) return '—';
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export default function MessageHistory({ refresh }) {
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchHistory = async () => {
        try {
            const data = await getHistory(20);
            setMessages(data.messages || []);
            setError(null);
        } catch (err) {
            setError('Could not load history — is the backend running?');
        } finally {
            setLoading(false);
        }
    };

    // Fetch on mount and whenever `refresh` changes (parent increments it on send)
    useEffect(() => {
        fetchHistory();
    }, [refresh]);

    return (
        <div className="history-card">
            <h2 className="card-title">Message History</h2>

            {loading && <p className="muted">Loading…</p>}
            {error && <p className="error-text">{error}</p>}

            {!loading && !error && messages.length === 0 && (
                <p className="muted">No messages sent yet.</p>
            )}

            <ul className="message-list">
                {messages.map((msg) => (
                    <li key={msg.id} className="message-item">
                        <span className="msg-text">{msg.text}</span>
                        <div className="msg-meta">
                            <span className={`delivery-badge ${msg.delivered ? 'delivered' : 'failed'}`}>
                                {msg.delivered ? '✓ Delivered' : '✗ Failed'}
                            </span>
                            {msg.latency_ms != null && (
                                <span className="latency">{msg.latency_ms} ms</span>
                            )}
                            <span className="msg-time">{formatTime(msg.timestamp)}</span>
                        </div>
                    </li>
                ))}
            </ul>
        </div>
    );
}
