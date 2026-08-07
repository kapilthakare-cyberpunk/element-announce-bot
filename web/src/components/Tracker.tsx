import React, { useState } from 'react';
import { Search, CheckCircle2, Clock, XCircle, Trash2, RefreshCw } from 'lucide-react';

interface RecipientStatus {
  name: string;
  room_id: string;
  event_id: string;
  status: 'confirmed' | 'pending' | 'failed';
  confirmed_at?: string | null;
}

interface Announcement {
  id: string;
  text: string;
  created_at: string;
  recipient_type: string;
  retracted?: boolean;
  members: Record<string, RecipientStatus>;
}

interface TrackerProps {
  apiBase: string;
  announcements: Announcement[];
  onRefresh: () => void;
}

export const Tracker: React.FC<TrackerProps> = ({ apiBase, announcements, onRefresh }) => {
  const [selectedAnnId, setSelectedAnnId] = useState<string>(announcements.length > 0 ? announcements[0].id : '');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'confirmed' | 'pending'>('all');

  const selectedAnnouncement = announcements.find(a => String(a.id) === String(selectedAnnId)) || announcements[0];

  const handleRetract = async (annId: string) => {
    if (!confirm('Are you sure you want to retract/redact this announcement from all DM rooms?')) return;
    try {
      await fetch(`${apiBase}/api/announcements/retract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: annId })
      });
      onRefresh();
    } catch (e) {
      console.error(e);
    }
  };

  const membersList = selectedAnnouncement ? Object.entries(selectedAnnouncement.members) : [];

  const filteredMembers = membersList.filter(([userId, rec]) => {
    const matchesSearch = rec.name.toLowerCase().includes(searchQuery.toLowerCase()) || userId.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || rec.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="astryx-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 700 }}>Live Delivery & Engagement Tracker</h2>
          <p style={{ color: 'var(--astryx-text-secondary)', fontSize: '13px', marginTop: '4px' }}>
            Monitor real-time ✅ reaction read confirmations across 1-on-1 DM rooms.
          </p>
        </div>
        <button className="astryx-btn astryx-btn-secondary" onClick={onRefresh}>
          <RefreshCw size={16} /> Refresh Status
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2.5fr', gap: '20px' }}>
        {/* Announcements Selection List */}
        <div className="astryx-card" style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '500px', overflowY: 'auto' }}>
          <h4 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--astryx-text-muted)', marginBottom: '4px' }}>
            ANNOUNCEMENT BROADCASTS
          </h4>
          {announcements.length === 0 && (
            <p style={{ fontSize: '13px', color: 'var(--astryx-text-muted)' }}>No announcements sent yet.</p>
          )}
          {announcements.map((ann) => {
            const confirmedCount = Object.values(ann.members).filter(m => m.status === 'confirmed').length;
            const totalCount = Object.keys(ann.members).length;
            const isSelected = String(ann.id) === String(selectedAnnId || selectedAnnouncement?.id);

            return (
              <div
                key={ann.id}
                onClick={() => setSelectedAnnId(ann.id)}
                style={{
                  padding: '12px',
                  borderRadius: 'var(--astryx-radius-sm)',
                  cursor: 'pointer',
                  border: isSelected ? '1px solid var(--astryx-primary)' : '1px solid var(--astryx-border-subtle)',
                  background: isSelected ? 'rgba(24, 119, 242, 0.1)' : 'var(--astryx-bg-canvas)',
                  transition: 'all 0.2s'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ fontWeight: 600, fontSize: '14px' }}>Broadcast #{ann.id}</span>
                  <span style={{ fontSize: '11px', color: 'var(--astryx-text-muted)' }}>{ann.created_at}</span>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--astryx-text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {ann.text}
                </p>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px', fontSize: '12px' }}>
                  <span className={`astryx-badge ${confirmedCount === totalCount ? 'badge-confirmed' : 'badge-pending'}`}>
                    {confirmedCount} / {totalCount} Confirmed
                  </span>
                  {ann.retracted && <span style={{ color: 'var(--astryx-accent-danger)', fontWeight: 600 }}>[RETRACTED]</span>}
                </div>
              </div>
            );
          })}
        </div>

        {/* Delivery Details Table Column */}
        {selectedAnnouncement ? (
          <div className="astryx-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h3 style={{ fontSize: '16px', fontWeight: 700 }}>Broadcast #{selectedAnnouncement.id} Details</h3>
                <p style={{ fontSize: '12px', color: 'var(--astryx-text-muted)', marginTop: '2px' }}>
                  Sent on {selectedAnnouncement.created_at} • Target: {selectedAnnouncement.recipient_type.toUpperCase()}
                </p>
              </div>
              {!selectedAnnouncement.retracted && (
                <button className="astryx-btn astryx-btn-danger" style={{ fontSize: '12px' }} onClick={() => handleRetract(selectedAnnouncement.id)}>
                  <Trash2 size={14} /> Retract Announcement
                </button>
              )}
            </div>

            {/* Announcement Message Content */}
            <div style={{ padding: '12px', background: 'var(--astryx-bg-canvas)', borderRadius: 'var(--astryx-radius-sm)', border: '1px solid var(--astryx-border-subtle)', fontSize: '13px', whiteSpace: 'pre-wrap' }}>
              {selectedAnnouncement.text}
            </div>

            {/* Controls Filter Bar */}
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1 }} className="astryx-input">
                <Search size={16} color="var(--astryx-text-muted)" />
                <input
                  type="text"
                  placeholder="Search member name or user ID..."
                  style={{ background: 'transparent', border: 'none', color: 'inherit', outline: 'none', width: '100%' }}
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', gap: '6px' }}>
                <button
                  className={`astryx-btn ${statusFilter === 'all' ? 'astryx-btn-primary' : 'astryx-btn-secondary'}`}
                  style={{ fontSize: '12px', padding: '6px 12px' }}
                  onClick={() => setStatusFilter('all')}
                >
                  All
                </button>
                <button
                  className={`astryx-btn ${statusFilter === 'confirmed' ? 'astryx-btn-primary' : 'astryx-btn-secondary'}`}
                  style={{ fontSize: '12px', padding: '6px 12px' }}
                  onClick={() => setStatusFilter('confirmed')}
                >
                  Confirmed
                </button>
                <button
                  className={`astryx-btn ${statusFilter === 'pending' ? 'astryx-btn-primary' : 'astryx-btn-secondary'}`}
                  style={{ fontSize: '12px', padding: '6px 12px' }}
                  onClick={() => setStatusFilter('pending')}
                >
                  Pending
                </button>
              </div>
            </div>

            {/* Recipient Delivery Status Table */}
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--astryx-border-subtle)', color: 'var(--astryx-text-muted)' }}>
                    <th style={{ padding: '10px' }}>TEAM MEMBER</th>
                    <th style={{ padding: '10px' }}>USER ID</th>
                    <th style={{ padding: '10px' }}>STATUS</th>
                    <th style={{ padding: '10px' }}>CONFIRMED AT</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredMembers.map(([userId, rec]) => (
                    <tr key={userId} style={{ borderBottom: '1px solid var(--astryx-border-subtle)' }}>
                      <td style={{ padding: '10px', fontWeight: 600 }}>{rec.name}</td>
                      <td style={{ padding: '10px', color: 'var(--astryx-text-secondary)', fontFamily: 'var(--astryx-font-mono)', fontSize: '12px' }}>
                        {userId}
                      </td>
                      <td style={{ padding: '10px' }}>
                        {rec.status === 'confirmed' ? (
                          <span className="astryx-badge badge-confirmed">
                            <CheckCircle2 size={12} /> Confirmed ✅
                          </span>
                        ) : rec.status === 'pending' ? (
                          <span className="astryx-badge badge-pending">
                            <Clock size={12} /> Pending ⏳
                          </span>
                        ) : (
                          <span className="astryx-badge badge-failed">
                            <XCircle size={12} /> Failed ❌
                          </span>
                        )}
                      </td>
                      <td style={{ padding: '10px', color: 'var(--astryx-text-muted)', fontSize: '12px' }}>
                        {rec.confirmed_at || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="astryx-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <p style={{ color: 'var(--astryx-text-muted)' }}>Select an announcement broadcast to view delivery tracking.</p>
          </div>
        )}
      </div>
    </div>
  );
};
