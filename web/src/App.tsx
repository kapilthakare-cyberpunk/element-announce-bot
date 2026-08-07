import { useState, useEffect } from 'react';
import { LayoutDashboard, Send, CheckSquare, Users, FileText, Settings as SettingsIcon, Zap } from 'lucide-react';
import { Dashboard } from './components/Dashboard';
import { BroadcastStudio } from './components/BroadcastStudio';
import { Tracker } from './components/Tracker';
import { MembersManager } from './components/MembersManager';
import { TemplatesManager } from './components/TemplatesManager';
import { Settings } from './components/Settings';

const API_BASE = 'http://127.0.0.1:8080';

export function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [platform, setPlatform] = useState<'matrix' | 'telegram'>('matrix');
  const [statusData, setStatusData] = useState<any>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [announcements, setAnnouncements] = useState<any[]>([]);

  const loadData = () => {
    fetch(`${API_BASE}/api/status`)
      .then(res => res.json())
      .then(setStatusData)
      .catch(console.error);

    fetch(`${API_BASE}/api/members`)
      .then(res => res.json())
      .then(data => setMembers(data.members || []))
      .catch(console.error);

    fetch(`${API_BASE}/api/announcements`)
      .then(res => res.json())
      .then(data => setAnnouncements(data.announcements || []))
      .catch(console.error);
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const stats = statusData?.stats || {
    total_members: members.length,
    test_members: members.filter(m => m.is_test).length,
    total_announcements: announcements.length,
    total_deliveries: 0,
    total_confirmed: 0,
    confirmation_rate_percent: 100.0
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--astryx-bg-canvas)' }}>
      {/* Astryx Meta Top Header Navigation */}
      <header className="astryx-glass" style={{ margin: '16px 24px', padding: '12px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderRadius: 'var(--astryx-radius-lg)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ background: 'linear-gradient(135deg, #0064e0 0%, #1877f2 100%)', width: '36px', height: '36px', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '20px', color: '#fff' }}>
            *
          </div>
          <div>
            <h1 style={{ fontSize: '18px', fontWeight: 700, letterSpacing: '-0.3px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              Element & Telegram Announce <span style={{ fontSize: '11px', background: 'var(--astryx-primary-glow)', color: 'var(--astryx-primary-hover)', padding: '2px 8px', borderRadius: 'var(--astryx-radius-full)', fontWeight: 600 }}>Astryx UI</span>
            </h1>
            <p style={{ fontSize: '11px', color: 'var(--astryx-text-muted)' }}>
              Powered by Meta Astryx Component Engine
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav style={{ display: 'flex', gap: '6px' }}>
          <button className={`astryx-btn ${activeTab === 'dashboard' ? 'astryx-btn-primary' : 'astryx-btn-secondary'}`} onClick={() => setActiveTab('dashboard')}>
            <LayoutDashboard size={16} /> Overview
          </button>
          <button className={`astryx-btn ${activeTab === 'broadcast' ? 'astryx-btn-primary' : 'astryx-btn-secondary'}`} onClick={() => setActiveTab('broadcast')}>
            <Send size={16} /> Broadcast Studio
          </button>
          <button className={`astryx-btn ${activeTab === 'tracker' ? 'astryx-btn-primary' : 'astryx-btn-secondary'}`} onClick={() => setActiveTab('tracker')}>
            <CheckSquare size={16} /> Delivery Tracker
          </button>
          <button className={`astryx-btn ${activeTab === 'members' ? 'astryx-btn-primary' : 'astryx-btn-secondary'}`} onClick={() => setActiveTab('members')}>
            <Users size={16} /> Members ({members.length})
          </button>
          <button className={`astryx-btn ${activeTab === 'templates' ? 'astryx-btn-primary' : 'astryx-btn-secondary'}`} onClick={() => setActiveTab('templates')}>
            <FileText size={16} /> Templates
          </button>
          <button className={`astryx-btn ${activeTab === 'settings' ? 'astryx-btn-primary' : 'astryx-btn-secondary'}`} onClick={() => setActiveTab('settings')}>
            <SettingsIcon size={16} /> Settings
          </button>
        </nav>

        {/* Live Platform Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="astryx-badge badge-confirmed" style={{ padding: '6px 12px', fontSize: '12px' }}>
            <Zap size={12} /> {platform === 'matrix' ? 'Matrix E2EE' : 'Telegram Bot API'} Live
          </span>
        </div>
      </header>

      {/* Main View Container */}
      <main style={{ flex: 1, padding: '0 24px 24px 24px', maxWidth: '1400px', margin: '0 auto', width: '100%' }}>
        {activeTab === 'dashboard' && <Dashboard stats={stats} platform={platform} onNavigate={setActiveTab} />}
        {activeTab === 'broadcast' && <BroadcastStudio apiBase={API_BASE} members={members} onBroadcastSuccess={loadData} />}
        {activeTab === 'tracker' && <Tracker apiBase={API_BASE} announcements={announcements} onRefresh={loadData} />}
        {activeTab === 'members' && <MembersManager apiBase={API_BASE} members={members} onRefresh={loadData} />}
        {activeTab === 'templates' && <TemplatesManager apiBase={API_BASE} />}
        {activeTab === 'settings' && <Settings platform={platform} onPlatformChange={setPlatform} />}
      </main>
    </div>
  );
}

export default App;
