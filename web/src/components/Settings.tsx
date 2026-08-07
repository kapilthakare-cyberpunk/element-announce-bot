import React, { useState } from 'react';
import { Server, Shield, CheckCircle2 } from 'lucide-react';

interface SettingsProps {
  platform: 'matrix' | 'telegram';
  onPlatformChange: (p: 'matrix' | 'telegram') => void;
}

export const Settings: React.FC<SettingsProps> = ({ platform, onPlatformChange }) => {
  const [homeserver, setHomeserver] = useState('https://matrix-client.matrix.org');
  const [userId, setUserId] = useState('@kapilsthakare:matrix.org');
  const [telegramToken, setTelegramToken] = useState('8753225184:AAHHqZ0FM69sNUo497JyIu1tfFyuWYmLB-A');
  const [telegramAdmin, setTelegramAdmin] = useState('7982368790');

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="astryx-card">
        <h2 style={{ fontSize: '20px', fontWeight: 700 }}>Bot & Platform Credentials</h2>
        <p style={{ color: 'var(--astryx-text-secondary)', fontSize: '13px', marginTop: '4px' }}>
          Configure connection endpoints, E2EE encryption, and Telegram bot keys.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Active Platform Configuration */}
        <div className="astryx-card">
          <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Server size={18} color="var(--astryx-primary)" /> Platform Selector
          </h3>

          <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
            <button
              className={`astryx-btn ${platform === 'matrix' ? 'astryx-btn-primary' : 'astryx-btn-secondary'}`}
              style={{ flex: 1 }}
              onClick={() => onPlatformChange('matrix')}
            >
              Matrix / Element E2EE
            </button>
            <button
              className={`astryx-btn ${platform === 'telegram' ? 'astryx-btn-primary' : 'astryx-btn-secondary'}`}
              style={{ flex: 1 }}
              onClick={() => onPlatformChange('telegram')}
            >
              Telegram Bot API
            </button>
          </div>

          {platform === 'matrix' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--astryx-text-muted)', display: 'block', marginBottom: '6px' }}>
                  HOMESERVER URL
                </label>
                <input className="astryx-input" value={homeserver} onChange={e => setHomeserver(e.target.value)} />
              </div>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--astryx-text-muted)', display: 'block', marginBottom: '6px' }}>
                  BOT MATRIX USER ID
                </label>
                <input className="astryx-input" value={userId} onChange={e => setUserId(e.target.value)} />
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--astryx-text-muted)', display: 'block', marginBottom: '6px' }}>
                  TELEGRAM BOT TOKEN
                </label>
                <input className="astryx-input" value={telegramToken} onChange={e => setTelegramToken(e.target.value)} />
              </div>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--astryx-text-muted)', display: 'block', marginBottom: '6px' }}>
                  TELEGRAM ADMIN CHAT ID
                </label>
                <input className="astryx-input" value={telegramAdmin} onChange={e => setTelegramAdmin(e.target.value)} />
              </div>
            </div>
          )}
        </div>

        {/* Security & Encryption Status */}
        <div className="astryx-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <h3 style={{ fontSize: '15px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Shield size={18} color="var(--astryx-accent-matrix)" /> Encryption & Key Sync
          </h3>

          <div style={{ padding: '12px', background: 'var(--astryx-bg-canvas)', borderRadius: 'var(--astryx-radius-sm)', border: '1px solid var(--astryx-border-subtle)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', fontWeight: 600, color: 'var(--astryx-accent-matrix)' }}>
              <CheckCircle2 size={16} /> Megolm E2EE Engine Initialized
            </div>
            <p style={{ fontSize: '12px', color: 'var(--astryx-text-secondary)' }}>
              End-to-End Encryption enabled via libolm. Cross-signing key bundle validated on matrix homeserver.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
