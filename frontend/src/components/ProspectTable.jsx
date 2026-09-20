import React, { useState, useEffect } from 'react';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { prospectsService, systemService } from '../lib/api';
import { AlertTriangle, User, ChevronDown, ChevronUp, Save } from 'lucide-react';

const STAGES = [
  'Discovered', 'Researched', 'Qualified', 'Drafted', 'Drafted_Linkedin',
  'Contacted', 'Engaged', 'Meeting', 'Opportunity', 'Rejected'
];

export default function ProspectTable({ campaignId }) {
  const [prospects, setProspects] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [expandedId, setExpandedId] = useState(null);
  const [reps, setReps] = useState([]);
  const [editData, setEditData] = useState({});
  const [saving, setSaving] = useState(false);
  const limit = 20;

  useEffect(() => {
    fetchProspects();
    fetchReps();
  }, [campaignId, page]);

  const fetchProspects = async () => {
    setLoading(true);
    try {
      const data = await prospectsService.getByCampaign(campaignId, { skip: page * limit, limit });
      setProspects(data.data || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error('Failed to fetch prospects', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchReps = async () => {
    try {
      const data = await systemService.getReps();
      setReps(data);
    } catch (err) {
      console.error('Failed to fetch reps', err);
    }
  };

  const getStageColor = (stage) => {
    const map = {
      'Discovered': 'default', 'Researched': 'primary', 'Qualified': 'primary',
      'Drafted': 'warning', 'Drafted_Linkedin': 'warning',
      'Contacted': 'success', 'Engaged': 'success', 'Meeting': 'success',
      'Opportunity': 'success', 'Rejected': 'danger', 'Draft_Failed': 'danger'
    };
    return map[stage] || 'default';
  };

  const toggleExpand = (id) => {
    if (expandedId === id) {
      setExpandedId(null);
    } else {
      setExpandedId(id);
      const p = prospects.find(pr => pr.id === id);
      setEditData({
        current_status: p.stage,
        notes: p.notes || '',
        assigned_rep_id: p.assigned_rep_id || ''
      });
    }
  };

  const handleSave = async (prospectId) => {
    setSaving(true);
    try {
      await prospectsService.update(prospectId, editData);
      setExpandedId(null);
      fetchProspects(); // Refresh
    } catch (err) {
      console.error('Failed to update prospect', err);
      alert('Update failed.');
    } finally {
      setSaving(false);
    }
  };

  const getName = (p) => {
    if (p.enriched_data?.name) return p.enriched_data.name;
    if (p.email) return p.email.split('@')[0].replace(/[._]/g, ' ');
    return 'Unknown Lead';
  };

  const getCompany = (p) => {
    if (p.enriched_data?.company) return p.enriched_data.company;
    if (p.email) return p.email.split('@')[1];
    return '';
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left">
        <thead className="text-xs text-slate-500 bg-slate-50 border-b border-slate-200 uppercase">
          <tr>
            <th className="px-6 py-4 font-medium">Name / Company</th>
            <th className="px-6 py-4 font-medium">Contact</th>
            <th className="px-6 py-4 font-medium">Stage</th>
            <th className="px-6 py-4 font-medium">Escalated</th>
            <th className="px-6 py-4 font-medium">Rep</th>
            <th className="px-6 py-4 font-medium text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr><td colSpan="6" className="px-6 py-8 text-center text-slate-500">Loading prospects...</td></tr>
          ) : prospects.length === 0 ? (
            <tr><td colSpan="6" className="px-6 py-8 text-center text-slate-500">No prospects found for this campaign.</td></tr>
          ) : (
            prospects.map((p) => (
              <React.Fragment key={p.id}>
                <tr className={`border-b border-slate-100 hover:bg-slate-50 transition-colors ${p.escalated_to_rep ? 'bg-red-50/40' : ''}`}>
                  <td className="px-6 py-4">
                    <div className="font-medium text-slate-900">{getName(p)}</div>
                    <div className="text-xs text-slate-500">{getCompany(p)}</div>
                  </td>
                  <td className="px-6 py-4 text-slate-600">
                    <div className="truncate max-w-[180px]">{p.email || 'N/A'}</div>
                    {p.linkedin_url && (
                      <a href={p.linkedin_url.startsWith('http') ? p.linkedin_url : `https://${p.linkedin_url}`} target="_blank" rel="noopener noreferrer" className="text-xs text-primary-600 hover:underline">LinkedIn</a>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <Badge variant={getStageColor(p.stage)}>{p.stage}</Badge>
                  </td>
                  <td className="px-6 py-4">
                    {p.escalated_to_rep ? (
                      <Badge variant="danger"><AlertTriangle className="w-3 h-3 mr-1" />Action Required</Badge>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-xs text-slate-600">
                    {p.assigned_rep_id ? reps.find(r => r.id === p.assigned_rep_id)?.name || p.assigned_rep_id : '—'}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Button variant="ghost" size="sm" onClick={() => toggleExpand(p.id)}>
                      {expandedId === p.id ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </Button>
                  </td>
                </tr>
                {/* Expanded edit row */}
                {expandedId === p.id && (
                  <tr className="bg-slate-50 border-b border-slate-200">
                    <td colSpan="6" className="px-6 py-4">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl">
                        <div>
                          <label className="block text-xs font-medium text-slate-600 mb-1">Override Stage</label>
                          <select
                            value={editData.current_status || ''}
                            onChange={e => setEditData({ ...editData, current_status: e.target.value })}
                            className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary-500 bg-white"
                          >
                            {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-slate-600 mb-1">Assign Rep</label>
                          <select
                            value={editData.assigned_rep_id || ''}
                            onChange={e => setEditData({ ...editData, assigned_rep_id: e.target.value })}
                            className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary-500 bg-white"
                          >
                            <option value="">Unassigned</option>
                            {reps.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-slate-600 mb-1">Notes</label>
                          <input
                            type="text"
                            value={editData.notes || ''}
                            onChange={e => setEditData({ ...editData, notes: e.target.value })}
                            className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary-500"
                            placeholder="Add notes..."
                          />
                        </div>
                      </div>
                      <div className="mt-3 flex items-center space-x-3">
                        <Button size="sm" onClick={() => handleSave(p.id)} disabled={saving}>
                          <Save className="w-4 h-4 mr-1.5" />{saving ? 'Saving...' : 'Save Changes'}
                        </Button>
                        {p.draft_email && (
                          <details className="text-xs">
                            <summary className="text-primary-600 cursor-pointer hover:underline">View Draft Email</summary>
                            <pre className="mt-2 bg-white p-3 border rounded text-slate-700 whitespace-pre-wrap max-w-xl">{p.draft_email}</pre>
                          </details>
                        )}
                        {p.draft_linkedin_msg && (
                          <details className="text-xs">
                            <summary className="text-primary-600 cursor-pointer hover:underline">View LinkedIn Draft</summary>
                            <pre className="mt-2 bg-white p-3 border rounded text-slate-700 whitespace-pre-wrap max-w-xl">{p.draft_linkedin_msg}</pre>
                          </details>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))
          )}
        </tbody>
      </table>
      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-6 py-3 border-t border-slate-100">
          <p className="text-xs text-slate-500">Showing {page * limit + 1}–{Math.min((page + 1) * limit, total)} of {total}</p>
          <div className="flex space-x-2">
            <Button variant="secondary" size="sm" disabled={page === 0} onClick={() => setPage(p => p - 1)}>Prev</Button>
            <Button variant="secondary" size="sm" disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}>Next</Button>
          </div>
        </div>
      )}
    </div>
  );
}
