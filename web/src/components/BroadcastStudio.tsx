import React, { useState, useEffect } from 'react';
import { Send, Eye, FileText, CheckCircle2, UserCheck, Users } from 'lucide-react';

interface Member {
  user_id: string;
  name: string;
  is_test: boolean;
}

interface Template {
  name: string;
  text: string;
}

interface BroadcastStudioProps {
  apiBase: string;
  members: Member[];
  onBroadcastSuccess: () => void;
}

export const BroadcastStudio: React.FC<BroadcastStudioProps> = ({ apiBase, members, onBroadcastSuccess }) => {
  const [text, setText] = useState('');
  const [templates, setTemplates] = useState<Template[]>([]);
  const [recipientType, setRecipientType] = useState<'all' | 'test' | 'custom'>('all');
  const [selectedCustomIds, setSelectedCustomIds] = useState<string[]>([]);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    fetch(`${apiBase}/api/templates`)
      .then(res => res.json())
      .then(data => setTemplates(data.templates || []))
      .catch(console.error);
  }, [apiBase]);

  const loadTemplate = (tmplText: string) => {
    setText(tmplText);
  };

  const toggleCustomUser = (userId: string) => {
    if (selectedCustomIds.includes(userId)) {
      setSelectedCustomIds(selectedCustomIds.filter(id => id !== userId));
    } else {
      setSelectedCustomIds([...selectedCustomIds, userId]);
    }
  };

  const getTargetCount = () => {
    if (recipientType === 'all') return members.length;
    if (recipientType === 'test') return members.filter(m => m.is_test).length;
    return selectedCustomIds.length;
  };

  const handleBroadcast = async () => {
    if (!text.trim()) return;
    setIsSending(true);
    try {
      const res = await fetch(`${apiBase}/api/broadcast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          recipient_type: recipientType,
          custom_user_ids: selectedCustomIds
        })
      });
      const data = await res.json();
      if (data.success) {
        setSuccessMessage(`Successfully broadcasted to ${data.target_count} member(s)!`);
        setText('');
        setTimeout(() => setSuccessMessage(''), 4000);
        onBroadcastSuccess();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsSending(false);
    }
  const fetchLatestPostLinks = async () => {
    setSuccessMessage('⚡ Scraping & fetching latest post URLs across IG, FB, LinkedIn & Telegram...');
    try {
      const res = await fetch(`${apiBase}/api/fetch_latest_links`);
      const data = await res.json();
      if (data.success && data.draft_text) {
        setText(data.draft_text);
        setSuccessMessage('⚡ Successfully fetched & drafted latest social media links!');
        setTimeout(() => setSuccessMessage(''), 4000);
      }
    } catch (e) {
      setSuccessMessage('❌ Failed to fetch latest links.');
    }
  };

  const sampleMemberName = members.length > 0 ? members[0].name : 'John Doe';
  const previewSample = text.replace(/<Name>/g, sampleMemberName);

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="astryx-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 700 }}>Announcement Broadcast Studio</h2>
          <p style={{ color: 'var(--astryx-text-secondary)', fontSize: '13px', marginTop: '4px' }}>
            Compose E2EE announcements, load templates, and target team members.
          </p>
        </div>
        {successMessage && (
          <div className="astryx-badge badge-confirmed" style={{ padding: '8px 16px', fontSize: '13px' }}>
            <CheckCircle2 size={16} /> {successMessage}
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>
        {/* Editor Column */}
        <div className="astryx-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Templates Quick Bar */}
          <div>
            <label style={{ fontSize: '13px', fontWeight: 600, color: 'var(--astryx-text-muted)', display: 'block', marginBottom: '8px' }}>
              LOAD TEMPLATE
            </label>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button
                className="astryx-btn astryx-btn-primary"
                style={{ fontSize: '12px', padding: '6px 14px', background: 'linear-gradient(135deg, #0088CC 0%, #00C6FF 100%)' }}
                onClick={fetchLatestPostLinks}
              >
                ⚡ Auto-Fetch Latest Post Links
              </button>
              {templates.map((t, idx) => (
                <button
                  key={idx}
                  className="astryx-btn astryx-btn-secondary"
                  style={{ fontSize: '12px', padding: '6px 12px' }}
                  onClick={() => loadTemplate(t.text)}
                >
                  <FileText size={14} /> {t.name}
                </button>
              ))}
            </div>
          </div>

          {/* Message Content Textarea */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <label style={{ fontSize: '13px', fontWeight: 600, color: 'var(--astryx-text-muted)' }}>
                ANNOUNCEMENT TEXT
              </label>
              <button
                className="astryx-btn astryx-btn-secondary"
                style={{ fontSize: '12px', padding: '4px 10px' }}
                onClick={() => setText(prev => prev + ' <Name>')}
              >
                + Insert &lt;Name&gt; Tag
              </button>
            </div>
            <textarea
              className="astryx-input astryx-textarea"
              style={{ minHeight: '200px' }}
              placeholder="Write announcement text here... Use <Name> for personal greeting."
              value={text}
              onChange={e => setText(e.target.value)}
            />
          </div>

          {/* Action Bar */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px' }}>
            <button
              className="astryx-btn astryx-btn-secondary"
              onClick={() => setIsPreviewOpen(!isPreviewOpen)}
            >
              <Eye size={16} /> {isPreviewOpen ? 'Hide Preview' : 'Live Preview'}
            </button>
            <button
              className="astryx-btn astryx-btn-primary"
              disabled={!text.trim() || getTargetCount() === 0 || isSending}
              onClick={handleBroadcast}
            >
              <Send size={16} /> {isSending ? 'Sending...' : `Broadcast to ${getTargetCount()} Recipient(s)`}
            </button>
          </div>
        </div>

        {/* Target & Preview Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Recipient Selection Card */}
          <div className="astryx-card">
            <h4 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px' }}>RECIPIENTS AUDIENCE</h4>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '14px', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="recipient"
                  checked={recipientType === 'all'}
                  onChange={() => setRecipientType('all')}
                />
                <Users size={16} /> All Team Members ({members.length})
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '14px', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="recipient"
                  checked={recipientType === 'test'}
                  onChange={() => setRecipientType('test')}
                />
                <UserCheck size={16} /> Test Users Only ({members.filter(m => m.is_test).length})
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '14px', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="recipient"
                  checked={recipientType === 'custom'}
                  onChange={() => setRecipientType('custom')}
                />
                Custom Selection ({selectedCustomIds.length})
              </label>
            </div>

            {recipientType === 'custom' && (
              <div style={{ marginTop: '14px', maxHeight: '160px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '6px', borderTop: '1px solid var(--astryx-border-subtle)', paddingTop: '10px' }}>
                {members.map(m => (
                  <label key={m.user_id} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={selectedCustomIds.includes(m.user_id)}
                      onChange={() => toggleCustomUser(m.user_id)}
                    />
                    {m.name}
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Live Preview Box */}
          {isPreviewOpen && (
            <div className="astryx-glass animate-fade-in" style={{ padding: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontSize: '12px', fontWeight: 600, color: 'var(--astryx-accent-matrix)' }}>
                <Eye size={14} /> DM LIVE PREVIEW (Sample for {sampleMemberName})
              </div>
              <div style={{ fontSize: '13px', whiteSpace: 'pre-wrap', lineHeight: 1.5, background: 'var(--astryx-bg-canvas)', padding: '12px', borderRadius: 'var(--astryx-radius-sm)', border: '1px solid var(--astryx-border-subtle)' }}>
                {previewSample || 'Type a message to see the live preview...'}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
