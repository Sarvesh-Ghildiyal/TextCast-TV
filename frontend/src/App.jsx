/**
 * App.jsx — Root component for the Text-to-TV Display System frontend.
 *
 * Layout:
 *   ┌─────────────────────────────────┐
 *   │  Header + ConnectionStatus      │
 *   ├──────────────────┬──────────────┤
 *   │  TextInput       │ MessageHist  │
 *   ├──────────────────┴──────────────┤
 *   │  PacketMonitor (placeholder)    │
 *   └─────────────────────────────────┘
 */

import { useState } from 'react';
import ConnectionStatus from './components/ConnectionStatus';
import TextInput from './components/TextInput';
import MessageHistory from './components/MessageHistory';
import PacketMonitor from './components/PacketMonitor';
import './App.css';

export default function App() {
  // Increment this to trigger MessageHistory to re-fetch after a send
  const [historyRefresh, setHistoryRefresh] = useState(0);

  const handleSent = () => setHistoryRefresh((n) => n + 1);

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="app-header">
        <div className="header-left">
          <span className="logo">📺</span>
          <div>
            <h1 className="app-title">Text to TV</h1>
            <p className="app-subtitle">Cast text to your Android TV via Chromecast</p>
          </div>
        </div>
        <ConnectionStatus />
      </header>

      {/* ── Main content ── */}
      <main className="app-main">
        <div className="top-grid">
          <TextInput onSent={handleSent} />
          <MessageHistory refresh={historyRefresh} />
        </div>
        <PacketMonitor />
      </main>

      {/* ── Footer ── */}
      <footer className="app-footer">
        <span>Phase 1 · Local Network · Flask + PyChromecast</span>
      </footer>
    </div>
  );
}
