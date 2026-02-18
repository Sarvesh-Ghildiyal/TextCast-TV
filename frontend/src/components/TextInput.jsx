/**
 * TextInput.jsx
 *
 * Main text input area with a "Send to TV" button.
 * Calls POST /api/cast/send and shows latency + success/error feedback.
 */

import { useState } from 'react';
import { sendText } from '../services/api';

export default function TextInput({ onSent }) {
    const [text, setText] = useState('');
    const [sending, setSending] = useState(false);
    const [feedback, setFeedback] = useState(null); // { type: 'success'|'error', msg }

    const handleSend = async () => {
        const trimmed = text.trim();
        if (!trimmed) return;

        setSending(true);
        setFeedback(null);

        try {
            const result = await sendText(trimmed);
            setFeedback({
                type: 'success',
                msg: `Sent! Latency: ${result.latency_ms ?? '—'} ms`,
            });
            if (onSent) onSent(trimmed);
            // Don't clear text — user may want to tweak and resend
        } catch (err) {
            const detail =
                err.response?.data?.error || err.message || 'Unknown error';
            setFeedback({ type: 'error', msg: `Failed: ${detail}` });
        } finally {
            setSending(false);
            // Auto-clear feedback after 4 seconds
            setTimeout(() => setFeedback(null), 4000);
        }
    };

    const handleKeyDown = (e) => {
        // Ctrl+Enter or Cmd+Enter to send
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            handleSend();
        }
    };

    return (
        <div className="text-input-card">
            <label className="input-label" htmlFor="tv-text">
                Message to display on TV
            </label>
            <textarea
                id="tv-text"
                className="tv-textarea"
                rows={4}
                placeholder="Type your message here…"
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={sending}
                maxLength={500}
            />
            <div className="input-footer">
                <span className="char-count">{text.length} / 500</span>
                <button
                    id="send-btn"
                    className={`send-btn ${sending ? 'sending' : ''}`}
                    onClick={handleSend}
                    disabled={sending || !text.trim()}
                >
                    {sending ? 'Sending…' : '📺 Send to TV'}
                </button>
            </div>
            {feedback && (
                <div className={`feedback ${feedback.type}`}>{feedback.msg}</div>
            )}
            <p className="hint">Tip: Press ⌘ + Enter to send quickly</p>
        </div>
    );
}
