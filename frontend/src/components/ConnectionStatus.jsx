/**
 * ConnectionStatus.jsx
 *
 * Polls GET /api/cast/status every 5 seconds and shows a live
 * green/red indicator with the TV name and IP.
 * Also provides a "Connect" button that calls POST /api/cast/connect.
 */

import { useEffect, useState } from 'react';
import { getStatus, disconnectFromTV } from '../services/api';
import api from '../services/api';

export default function ConnectionStatus() {
    const [status, setStatus] = useState({
        online: false,
        device_name: 'Living Room TV',
        device_ip: '192.168.29.28',
    });
    const [loading, setLoading] = useState(true);
    const [connecting, setConnecting] = useState(false);
    const [disconnecting, setDisconnecting] = useState(false);
    const [feedback, setFeedback] = useState(null); // { type: 'success'|'error', msg }

    const fetchStatus = async () => {
        try {
            const data = await getStatus();
            setStatus(data);
        } catch {
            setStatus((prev) => ({ ...prev, online: false }));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStatus();
        const interval = setInterval(fetchStatus, 5000);
        return () => clearInterval(interval);
    }, []);

    const handleConnect = async () => {
        setConnecting(true);
        setFeedback(null);
        try {
            const res = await api.post('/api/cast/connect');
            const data = res.data;
            if (data.success) {
                setFeedback({ type: 'success', msg: data.message });
                // Immediately refresh status so dot turns green
                await fetchStatus();
            } else {
                setFeedback({ type: 'error', msg: data.error || 'Connection failed' });
            }
        } catch (err) {
            const detail = err.response?.data?.error || err.message || 'Unknown error';
            setFeedback({ type: 'error', msg: `Failed: ${detail}` });
        } finally {
            setConnecting(false);
            setTimeout(() => setFeedback(null), 5000);
        }
    };

    const handleDisconnect = async () => {
        setDisconnecting(true);
        setFeedback(null);
        try {
            const data = await disconnectFromTV();
            if (data.success) {
                setFeedback({ type: 'success', msg: data.message });
                await fetchStatus();
            } else {
                setFeedback({ type: 'error', msg: data.error || 'Disconnect failed' });
            }
        } catch (err) {
            const detail = err.response?.data?.error || err.message || 'Unknown error';
            setFeedback({ type: 'error', msg: `Disconnect failed: ${detail}` });
        } finally {
            setDisconnecting(false);
            setTimeout(() => setFeedback(null), 5000);
        }
    };

    return (
        <div className="status-card">
            <div className="status-top-row">
                <div className="status-indicator">
                    <div className={`status-dot ${status.online ? 'online' : 'offline'}`} />
                    <div className="status-info">
                        <span className="status-label">
                            {loading ? 'Checking…' : status.online ? 'Connected' : 'Offline'}
                        </span>
                        <span className="status-device">
                            {status.device_name} · {status.device_ip}
                        </span>
                    </div>
                </div>
                <div className="button-group">
                    <button
                        id="connect-btn"
                        className={`connect-btn ${connecting ? 'connecting' : ''} ${status.online ? 'reconnect' : ''}`}
                        onClick={handleConnect}
                        disabled={connecting || disconnecting}
                    >
                        {connecting ? 'Connecting…' : status.online ? '🔄 Reconnect' : '🔌 Connect'}
                    </button>
                    {status.online && (
                        <button
                            id="disconnect-btn"
                            className={`disconnect-btn ${disconnecting ? 'disconnecting' : ''}`}
                            onClick={handleDisconnect}
                            disabled={connecting || disconnecting}
                        >
                            {disconnecting ? 'Wait…' : '🛑 Disconnect'}
                        </button>
                    )}
                </div>
            </div>
            {feedback && (
                <div className={`connect-feedback ${feedback.type}`}>
                    {feedback.msg}
                </div>
            )}
        </div>
    );
}
