import React from 'react';
import { Send, CheckCircle2, Users, ShieldCheck, AlertCircle, MessageSquare } from 'lucide-react';

interface Stats {
  total_members: number;
  test_members: number;
  total_announcements: number;
  total_deliveries: number;
  total_confirmed: number;
  confirmation_rate_percent: number;
}

interface DashboardProps {
  stats: Stats;
  platform: 'matrix' | 'telegram';
  onNavigate: (tab: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ stats, platform, onNavigate }) => {
  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header Banner */}
      <div className="astryx-glass" style={{ padding: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '6px' }}>
            {platform === 'matrix' ? 'Matrix / Element Hub' : 'Telegram Broadcast Hub'}
          </h2>
          <p style={{ color: 'var(--astryx-text-secondary)', fontSize: '14px' }}>
            Encrypted team announcements & live reaction confirmation tracking system
          </p>
        </div>
        <button className="astryx-btn astryx-btn-primary" onClick={() => onNavigate('broadcast')}>
          <Send size={16} /> New Broadcast
        </button>
      </div>

      {/* Metric Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
        <div className="astryx-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--astryx-text-muted)', marginBottom: '12px' }}>
            <span style={{ fontSize: '13px', fontWeight: 600 }}>CONFIRMATION RATE</span>
            <CheckCircle2 size={20} color="var(--astryx-accent-matrix)" />
          </div>
          <div style={{ fontSize: '32px', fontWeight: 700, color: 'var(--astryx-text-primary)' }}>
            {stats.confirmation_rate_percent}%
          </div>
          <p style={{ fontSize: '12px', color: 'var(--astryx-text-secondary)', marginTop: '4px' }}>
            {stats.total_confirmed} of {stats.total_deliveries} confirmed
          </p>
        </div>

        <div className="astryx-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--astryx-text-muted)', marginBottom: '12px' }}>
            <span style={{ fontSize: '13px', fontWeight: 600 }}>TEAM MEMBERS</span>
            <Users size={20} color="var(--astryx-primary-hover)" />
          </div>
          <div style={{ fontSize: '32px', fontWeight: 700 }}>{stats.total_members}</div>
          <p style={{ fontSize: '12px', color: 'var(--astryx-text-secondary)', marginTop: '4px' }}>
            {stats.test_members} test accounts registered
          </p>
        </div>

        <div className="astryx-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--astryx-text-muted)', marginBottom: '12px' }}>
            <span style={{ fontSize: '13px', fontWeight: 600 }}>ANNOUNCEMENTS</span>
            <MessageSquare size={20} color="var(--astryx-accent-telegram)" />
          </div>
          <div style={{ fontSize: '32px', fontWeight: 700 }}>{stats.total_announcements}</div>
          <p style={{ fontSize: '12px', color: 'var(--astryx-text-secondary)', marginTop: '4px' }}>
            Total broadcasts dispatched
          </p>
        </div>

        <div className="astryx-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--astryx-text-muted)', marginBottom: '12px' }}>
            <span style={{ fontSize: '13px', fontWeight: 600 }}>E2EE SECURITY</span>
            <ShieldCheck size={20} color="var(--astryx-accent-matrix)" />
          </div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--astryx-accent-matrix)' }}>
            Active (Megolm)
          </div>
          <p style={{ fontSize: '12px', color: 'var(--astryx-text-secondary)', marginTop: '4px' }}>
            1-on-1 Encrypted DMs
          </p>
        </div>
      </div>

      {/* Quick Actions Panel */}
      <div className="astryx-card" style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
        <AlertCircle size={20} color="var(--astryx-primary-hover)" />
        <div style={{ flex: 1 }}>
          <h4 style={{ fontSize: '15px', fontWeight: 600 }}>System Ready</h4>
          <p style={{ fontSize: '13px', color: 'var(--astryx-text-secondary)' }}>
            All registered members have active 1-on-1 DM rooms. Ready for next broadcast.
          </p>
        </div>
        <button className="astryx-btn astryx-btn-secondary" onClick={() => onNavigate('tracker')}>
          View Deliveries
        </button>
      </div>
    </div>
  );
};
