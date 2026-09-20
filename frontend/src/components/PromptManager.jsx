import React, { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';
import { campaignsService } from '../lib/api';
import { Cpu, Plus, Check } from 'lucide-react';

const AGENT_TYPES = [
  { value: 'icp_fitment', label: 'ICP Fitment Agent' },
  { value: 'email_drafter', label: 'Email Drafter Agent' },
  { value: 'linkedin_drafter', label: 'LinkedIn Drafter Agent' },
  { value: 'personalization', label: 'Personalization Agent' },
  { value: 'conversation_handler', label: 'Conversation Handler' },
];

export default function PromptManager({ campaignId }) {
  const [prompts, setPrompts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ agent_type: 'icp_fitment', prompt_text: '' });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchPrompts();
  }, [campaignId]);

  const fetchPrompts = async () => {
    setLoading(true);
    try {
      const data = await campaignsService.getPrompts(campaignId);
      setPrompts(data);
    } catch (err) {
      console.error('Failed to fetch prompts', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!formData.prompt_text.trim()) return;
    setSaving(true);
    try {
      await campaignsService.createPrompt(campaignId, formData);
      setFormData({ agent_type: 'icp_fitment', prompt_text: '' });
      setShowForm(false);
      fetchPrompts();
    } catch (err) {
      console.error('Failed to create prompt', err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between border-b border-slate-100">
        <div className="flex items-center space-x-2">
          <Cpu className="w-5 h-5 text-primary-600" />
          <CardTitle>Prompt Versions</CardTitle>
        </div>
        <Button variant="secondary" size="sm" onClick={() => setShowForm(!showForm)}>
          <Plus className="w-4 h-4 mr-1.5" /> New Prompt
        </Button>
      </CardHeader>
      <CardContent className="p-6">
        {showForm && (
          <form onSubmit={handleCreate} className="mb-6 p-4 border border-slate-200 rounded-lg bg-slate-50 space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Agent Type</label>
              <select
                value={formData.agent_type}
                onChange={e => setFormData({ ...formData, agent_type: e.target.value })}
                className="w-full border border-slate-300 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none bg-white"
              >
                {AGENT_TYPES.map(t => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Prompt Text</label>
              <textarea
                value={formData.prompt_text}
                onChange={e => setFormData({ ...formData, prompt_text: e.target.value })}
                rows={4}
                className="w-full border border-slate-300 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none resize-y font-mono text-sm"
                placeholder="Enter the system prompt for this agent..."
                required
              />
            </div>
            <div className="flex justify-end space-x-2">
              <Button type="button" variant="ghost" onClick={() => setShowForm(false)}>Cancel</Button>
              <Button type="submit" disabled={saving}>
                {saving ? 'Saving...' : 'Save & Activate'}
              </Button>
            </div>
          </form>
        )}

        {loading ? (
          <p className="text-sm text-slate-500">Loading prompts...</p>
        ) : prompts.length === 0 ? (
          <p className="text-sm text-slate-500">No active prompts configured. Click "New Prompt" to create one.</p>
        ) : (
          <div className="space-y-4">
            {prompts.map(p => (
              <div key={p.id} className="border border-slate-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-semibold text-slate-900">
                      {AGENT_TYPES.find(a => a.value === p.agent_type)?.label || p.agent_type}
                    </span>
                    <Badge variant="primary">v{p.version_number}</Badge>
                    {p.is_active && (
                      <Badge variant="success"><Check className="w-3 h-3 mr-1" />Active</Badge>
                    )}
                  </div>
                  <span className="text-xs text-slate-400">{new Date(p.created_at).toLocaleDateString()}</span>
                </div>
                <pre className="text-xs text-slate-600 bg-slate-50 p-3 rounded overflow-x-auto whitespace-pre-wrap">
                  {p.prompt_text}
                </pre>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
