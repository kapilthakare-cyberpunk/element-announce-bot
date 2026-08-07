import React, { useState } from 'react';
import { UserPlus, Search, Trash2, UserCheck } from 'lucide-react';

interface Member {
  user_id: string;
  name: string;
  is_test: boolean;
}

interface MembersManagerProps {
  apiBase: string;
  members: Member[];
  onRefresh: () => void;
}

export const MembersManager: React.FC<MembersManagerProps> = ({ apiBase, members, onRefresh }) => {
  const [search, setSearch] = useState('');
  const [newUserId, setNewUserId] = useState('');
  const [newName, setNewName] = useState('');
  const [newIsTest, setNewIsTest] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const handleAddOrUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUserId.trim() || !newName.trim()) return;

    setIsSaving(true);
    try {
      await fetch(`${apiBase}/api/members`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: newUserId.trim(),
          name: newName.trim(),
          is_test: newIsTest
        })
      });
      setNewUserId('');
      setNewName('');
      setNewIsTest(false);
      onRefresh();
    } catch (err) {
      console.error(err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (userId: string) => {
    if (!confirm(`Are you sure you want to remove ${userId}?`)) return;
    try {
      await fetch(`${apiBase}/api/members?user_id=${encodeURIComponent(userId)}`, {
        method: 'DELETE'
      });
      onRefresh();
    } catch (err) {
      console.error(err);
    }
  };

  const filteredMembers = members.filter(
    m => m.name.toLowerCase().includes(search.toLowerCase()) || m.user_id.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="astryx-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 700 }}>Team Member Directory</h2>
          <p style={{ color: 'var(--astryx-text-secondary)', fontSize: '13px', marginTop: '4px' }}>
            Manage registered Matrix and Telegram team accounts and test groups.
          </p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 2fr', gap: '20px' }}>
        {/* Add/Edit Member Form */}
        <div className="astryx-card">
          <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <UserPlus size={18} color="var(--astryx-primary)" /> Register / Edit Member
          </h3>

          <form onSubmit={handleAddOrUpdate} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--astryx-text-muted)', display: 'block', marginBottom: '6px' }}>
                MATRIX USER ID / TELEGRAM USER ID
              </label>
              <input
                type="text"
                className="astryx-input"
                placeholder="@username:matrix.org or 7982368790"
                value={newUserId}
                onChange={e => setNewUserId(e.target.value)}
                required
              />
            </div>

            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--astryx-text-muted)', display: 'block', marginBottom: '6px' }}>
                FULL NAME
              </label>
              <input
                type="text"
                className="astryx-input"
                placeholder="e.g. Kapil Thakare"
                value={newName}
                onChange={e => setNewName(e.target.value)}
                required
              />
            </div>

            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', cursor: 'pointer', marginTop: '4px' }}>
              <input
                type="checkbox"
                checked={newIsTest}
                onChange={e => setNewIsTest(e.target.checked)}
              />
              Mark as Test Recipient Account
            </label>

            <button
              type="submit"
              className="astryx-btn astryx-btn-primary"
              disabled={isSaving}
              style={{ marginTop: '8px' }}
            >
              {isSaving ? 'Saving...' : 'Save Team Member'}
            </button>
          </form>
        </div>

        {/* Member Directory Table */}
        <div className="astryx-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="astryx-input" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Search size={16} color="var(--astryx-text-muted)" />
            <input
              type="text"
              placeholder="Search members by name or handle..."
              style={{ background: 'transparent', border: 'none', color: 'inherit', outline: 'none', width: '100%' }}
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--astryx-border-subtle)', color: 'var(--astryx-text-muted)' }}>
                  <th style={{ padding: '10px' }}>NAME</th>
                  <th style={{ padding: '10px' }}>USER ID</th>
                  <th style={{ padding: '10px' }}>TEST GROUP</th>
                  <th style={{ padding: '10px', textAlign: 'right' }}>ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {filteredMembers.map(m => (
                  <tr key={m.user_id} style={{ borderBottom: '1px solid var(--astryx-border-subtle)' }}>
                    <td style={{ padding: '10px', fontWeight: 600 }}>{m.name}</td>
                    <td style={{ padding: '10px', fontFamily: 'var(--astryx-font-mono)', fontSize: '12px', color: 'var(--astryx-text-secondary)' }}>
                      {m.user_id}
                    </td>
                    <td style={{ padding: '10px' }}>
                      {m.is_test ? (
                        <span className="astryx-badge badge-confirmed">
                          <UserCheck size={12} /> Test User
                        </span>
                      ) : (
                        <span style={{ color: 'var(--astryx-text-muted)', fontSize: '12px' }}>Standard</span>
                      )}
                    </td>
                    <td style={{ padding: '10px', textAlign: 'right' }}>
                      <button
                        className="astryx-btn astryx-btn-danger"
                        style={{ padding: '4px 8px', fontSize: '12px' }}
                        onClick={() => handleDelete(m.user_id)}
                      >
                        <Trash2 size={14} /> Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
