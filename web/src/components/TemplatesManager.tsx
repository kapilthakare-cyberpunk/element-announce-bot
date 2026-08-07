import React, { useState, useEffect } from 'react';
import { FileText, Plus, Trash2, Save, Edit3 } from 'lucide-react';

interface Template {
  name: string;
  text: string;
}

interface TemplatesManagerProps {
  apiBase: string;
}

export const TemplatesManager: React.FC<TemplatesManagerProps> = ({ apiBase }) => {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [name, setName] = useState('');
  const [text, setText] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const fetchTemplates = async () => {
    try {
      const res = await fetch(`${apiBase}/api/templates`);
      const data = await res.json();
      setTemplates(data.templates || []);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, [apiBase]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !text.trim()) return;

    setIsSaving(true);
    try {
      await fetch(`${apiBase}/api/templates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), text: text.trim() })
      });
      setName('');
      setText('');
      fetchTemplates();
    } catch (e) {
      console.error(e);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (tmplName: string) => {
    if (!confirm(`Are you sure you want to delete template "${tmplName}"?`)) return;
    try {
      await fetch(`${apiBase}/api/templates?name=${encodeURIComponent(tmplName)}`, {
        method: 'DELETE'
      });
      fetchTemplates();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="astryx-card">
        <h2 style={{ fontSize: '20px', fontWeight: 700 }}>Announcement Templates Manager</h2>
        <p style={{ color: 'var(--astryx-text-secondary)', fontSize: '13px', marginTop: '4px' }}>
          Create and manage reusable message templates for recurring team broadcasts.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '20px' }}>
        {/* Template Form */}
        <div className="astryx-card">
          <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Plus size={18} color="var(--astryx-primary)" /> Save / Update Template
          </h3>

          <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--astryx-text-muted)', display: 'block', marginBottom: '6px' }}>
                TEMPLATE TITLE
              </label>
              <input
                type="text"
                className="astryx-input"
                placeholder="e.g. Social Media Reel Engagement"
                value={name}
                onChange={e => setName(e.target.value)}
                required
              />
            </div>

            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--astryx-text-muted)', display: 'block', marginBottom: '6px' }}>
                TEMPLATE BODY (Use &lt;Name&gt; tag for member greeting)
              </label>
              <textarea
                className="astryx-input astryx-textarea"
                style={{ minHeight: '160px' }}
                placeholder="Hi <Name>,\n\nPlease engage with our social posts..."
                value={text}
                onChange={e => setText(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="astryx-btn astryx-btn-primary" disabled={isSaving}>
              <Save size={16} /> {isSaving ? 'Saving...' : 'Save Template'}
            </button>
          </form>
        </div>

        {/* Existing Templates Grid */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {templates.map((t, idx) => (
            <div key={idx} className="astryx-card" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h4 style={{ fontSize: '15px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <FileText size={16} color="var(--astryx-accent-telegram)" /> {t.name}
                </h4>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <button
                    className="astryx-btn astryx-btn-secondary"
                    style={{ padding: '4px 8px', fontSize: '12px' }}
                    onClick={() => { setName(t.name); setText(t.text); }}
                  >
                    <Edit3 size={14} /> Edit
                  </button>
                  <button
                    className="astryx-btn astryx-btn-danger"
                    style={{ padding: '4px 8px', fontSize: '12px' }}
                    onClick={() => handleDelete(t.name)}
                  >
                    <Trash2 size={14} /> Delete
                  </button>
                </div>
              </div>
              <p style={{ fontSize: '13px', color: 'var(--astryx-text-secondary)', whiteSpace: 'pre-wrap', maxHeight: '100px', overflowY: 'auto' }}>
                {t.text}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
