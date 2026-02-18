/**
 * PacketMonitor.jsx
 *
 * Polls GET /api/packets/stats every 3 seconds and displays:
 *   - Total packets captured & total bytes
 *   - Protocol breakdown (TCP / UDP / Other)
 *   - Live list of the 20 most recent packets
 */

import { useEffect, useState } from 'react';
import { getPacketStats } from '../services/api';

function formatBytes(bytes) {
    if (bytes == null) return '—';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatTime(isoString) {
    if (!isoString) return '—';
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export default function PacketMonitor() {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchStats = async () => {
        try {
            const data = await getPacketStats();
            setStats(data);
            setError(null);
        } catch (err) {
            setError('Could not load packet stats — is the backend running?');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStats();
        const interval = setInterval(fetchStats, 3000);
        return () => clearInterval(interval);
    }, []);

    const totalPackets = stats?.total_packets ?? 0;
    const totalBytes = stats?.total_bytes ?? 0;
    const breakdown = stats?.protocol_breakdown ?? {};
    const recentPackets = stats?.recent_packets ?? [];

    return (
        <div className="packet-card">
            <div className="packet-header">
                <h2 className="card-title">📡 Packet Monitor</h2>
                <span className={`packet-live-badge ${totalPackets > 0 ? 'active' : 'idle'}`}>
                    {totalPackets > 0 ? '● LIVE' : '○ Idle'}
                </span>
            </div>

            {loading && <p className="muted">Loading…</p>}
            {error && <p className="error-text">{error}</p>}

            {!loading && !error && (
                <>
                    {/* ── Summary stats ── */}
                    <div className="packet-stats-grid">
                        <div className="packet-stat-box">
                            <span className="stat-value">{totalPackets.toLocaleString()}</span>
                            <span className="stat-label">Total Packets</span>
                        </div>
                        <div className="packet-stat-box">
                            <span className="stat-value">{formatBytes(totalBytes)}</span>
                            <span className="stat-label">Total Data</span>
                        </div>
                        {Object.entries(breakdown).map(([proto, count]) => (
                            <div key={proto} className="packet-stat-box">
                                <span className="stat-value">{count.toLocaleString()}</span>
                                <span className="stat-label">{proto}</span>
                            </div>
                        ))}
                    </div>

                    {/* ── Recent packets table ── */}
                    {recentPackets.length === 0 ? (
                        <p className="muted">
                            No packets captured yet. Connect to the TV to start monitoring.
                        </p>
                    ) : (
                        <div className="packet-table-wrapper">
                            <table className="packet-table">
                                <thead>
                                    <tr>
                                        <th>Protocol</th>
                                        <th>Source</th>
                                        <th>Destination</th>
                                        <th>Size</th>
                                        <th>Time</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {recentPackets.map((pkt) => (
                                        <tr key={pkt.id}>
                                            <td>
                                                <span className={`proto-badge proto-${(pkt.protocol || 'other').toLowerCase()}`}>
                                                    {pkt.protocol || '?'}
                                                </span>
                                            </td>
                                            <td className="mono">{pkt.source_ip}</td>
                                            <td className="mono">{pkt.dest_ip}</td>
                                            <td>{formatBytes(pkt.size_bytes)}</td>
                                            <td>{formatTime(pkt.timestamp)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
