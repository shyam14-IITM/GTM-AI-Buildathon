import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import Header from '../components/layout/Header';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import ProspectTable from '../components/ProspectTable';
import AgentLogs from '../components/AgentLogs';
import KnowledgeUpload from '../components/KnowledgeUpload';
import PromptManager from '../components/PromptManager';
import { campaignsService } from '../lib/api';
import { ArrowLeft, Play, Pause, Rocket, Users, Zap } from 'lucide-react';

const TABS = [
  { key: 'overview', label: 'Overview' },
  { key: 'prospects', label: 'Prospects' },
  { key: 'prompts', label: 'Prompt & Settings' },
  { key: 'knowledge', label: 'Knowledge Base' },
  { key: 'logs', label: 'Agent Logs' },
];

export default function CampaignDetail() {
  const { id } = useParams();
  const [campaign, setCampaign] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [executing, setExecuting] = useState(false);
  const [discovering, setDiscovering] = useState(false);
  const [actionMsg, setActionMsg] = useState('');

  useEffect(() => {
    fetchData();
  }, [id]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [allCampaigns, metricsData] = await Promise.all([
        campaignsService.getAll(),
        campaignsService.getMetrics(id).catch(() => null),
      ]);

      const foundCampaign = allCampaigns.find(c => c.id === id);
      setCampaign(foundCampaign || null);
      if (metricsData) setMetrics(metricsData);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleStatus = async () => {
    if (!campaign) return;
    let newStatus;
    if (campaign.status === 'Draft') newStatus = 'Live';
    else if (campaign.status === 'Live') newStatus = 'Paused';
    else newStatus = 'Live'; // Paused → Live
    try {
      const updated = await campaignsService.update(id, { status: newStatus });
      setCampaign(updated);
    } catch (err) {
      console.error(err);
    }
  };

  const handleExecute = async () => {
    setExecuting(true);
    setActionMsg('');
    try {
      const res = await campaignsService.execute(id);
      setActionMsg(`✅ ${res.message} — ${res.queued} prospects queued.`);
    } catch (err) {
      const detail = err.response?.data?.detail || 'Execution failed.';
      setActionMsg(`❌ ${detail}`);
    } finally {
      setExecuting(false);
    }
  };

  const handleDiscover = async () => {
    setDiscovering(true);
    setActionMsg('');
    try {
      const res = await campaignsService.discover(id);
      setActionMsg(`✅ ${res.message}`);
      // Refresh metrics
      const metricsData = await campaignsService.getMetrics(id).catch(() => null);
      if (metricsData) setMetrics(metricsData);
    } catch (err) {
      const detail = err.response?.data?.detail || 'Discovery failed.';
      setActionMsg(`❌ ${detail}`);
    } finally {
      setDiscovering(false);
    }
  };

  if (loading) return <div className="p-8 text-center text-slate-500">Loading campaign details...</div>;
  if (!campaign) return <div className="p-8 text-center text-red-500">Campaign not found.</div>;

  const isLive = campaign.status === 'Live';
  const maxFunnel = metrics ? Math.max(metrics.discovered || 1, 1) : 1;
  const getWidth = (val) => `${Math.max(((val || 0) / maxFunnel) * 100, 8)}%`;

  const funnelStages = metrics ? [
    { label: 'Discovered', value: metrics.discovered, color: 'bg-blue-200' },
    { label: 'Researched', value: metrics.researched, color: 'bg-blue-300' },
    { label: 'Qualified', value: metrics.qualified, color: 'bg-blue-400' },
    { label: 'Contacted', value: metrics.contacted, color: 'bg-blue-500' },
    { label: 'Engaged', value: metrics.engaged, color: 'bg-blue-600' },
    { label: 'Meeting', value: metrics.meeting, color: 'bg-blue-700' },
    { label: 'Opportunity', value: metrics.opportunity, color: 'bg-blue-800' },
  ] : [];

  return (
    <>
      <Header title={
        <div className="flex items-center space-x-3">
          <Link to="/dashboard" className="text-slate-400 hover:text-slate-600">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <span>{campaign.name}</span>
          <Badge variant={isLive ? 'success' : campaign.status === 'Paused' ? 'warning' : 'default'}>
            <span className="w-1.5 h-1.5 rounded-full bg-current mr-1.5 inline-block"></span>
            {campaign.status}
          </Badge>
        </div>
      } />

      <div className="max-w-7xl mx-auto mt-6 space-y-6">
        {/* Status-Aware Action Bar */}
        {campaign.status === 'Draft' && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-amber-800">This campaign is in Draft mode.</p>
              <p className="text-xs text-amber-700 mt-0.5">Set it to Live before you can discover prospects and execute AI agents.</p>
            </div>
            <Button onClick={handleToggleStatus}>
              <Play className="w-4 h-4 mr-2" /> Go Live
            </Button>
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            {campaign.status !== 'Draft' && (
              <Button variant="secondary" onClick={handleToggleStatus}>
                {isLive ? <Pause className="w-4 h-4 mr-2" /> : <Play className="w-4 h-4 mr-2" />}
                {isLive ? 'Pause Campaign' : 'Resume Campaign'}
              </Button>
            )}
          </div>
          <div className="flex items-center gap-3">
            <Button variant="secondary" onClick={handleDiscover} disabled={discovering || campaign.status === 'Draft'}>
              <Users className="w-4 h-4 mr-2" />{discovering ? 'Searching...' : 'Discover Leads'}
            </Button>
            <Button onClick={handleExecute} disabled={executing || !isLive}>
              <Rocket className="w-4 h-4 mr-2" />{executing ? 'Starting Agents...' : 'Execute AI Agents'}
            </Button>
          </div>
        </div>

        {!isLive && campaign.status !== 'Draft' && (
          <div className="bg-slate-100 border border-slate-200 rounded-lg p-3 text-sm text-slate-600">
            ⚠️ Campaign is <strong>{campaign.status}</strong>. Set it to <strong>Live</strong> to execute AI agents.
          </div>
        )}

        {actionMsg && (
          <div className="p-3 bg-slate-100 rounded-lg text-sm text-slate-700">{actionMsg}</div>
        )}

        {/* Tabs */}
        <div className="border-b border-slate-200">
          <nav className="flex space-x-8">
            {TABS.map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`py-3 px-1 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.key
                    ? 'border-primary-600 text-primary-600'
                    : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Campaign Info */}
            <Card>
              <CardHeader><CardTitle>Campaign Info</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-xs text-slate-500 mb-1">Target Roles</p>
                  <p className="text-sm font-medium">
                    {campaign.targeting_criteria?.roles?.join(', ') || 'Not set'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Company Size</p>
                  <p className="text-sm font-medium">{campaign.targeting_criteria?.company_size || 'Any'}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Geography</p>
                  <p className="text-sm font-medium">{campaign.targeting_criteria?.geography || 'Global'}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Industry</p>
                  <p className="text-sm font-medium">{campaign.targeting_criteria?.industry || 'All'}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Channels</p>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {campaign.config?.is_email_enabled && <Badge variant="primary">Email</Badge>}
                    {campaign.config?.is_linkedin_enabled && <Badge variant="primary">LinkedIn</Badge>}
                    {campaign.config?.is_voice_enabled && <Badge variant="primary">Voice</Badge>}
                  </div>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Assigned Rep</p>
                  <p className="text-sm font-medium">{campaign.config?.assigned_rep?.name || 'Unassigned'}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Daily Limit</p>
                  <p className="text-sm font-medium">{campaign.config?.daily_limit || 'Unlimited'}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Created</p>
                  <p className="text-sm font-medium">{new Date(campaign.created_at).toLocaleDateString()}</p>
                </div>
              </CardContent>
            </Card>

            {/* Funnel */}
            <Card className="lg:col-span-2">
              <CardHeader><CardTitle>Prospect Pipeline</CardTitle></CardHeader>
              <CardContent>
                {funnelStages.length > 0 ? (
                  <div className="space-y-2 mt-2">
                    {funnelStages.map((stage) => (
                      <div key={stage.label} className="flex items-center gap-4">
                        <span className="text-xs text-slate-500 w-24 text-right shrink-0">{stage.label}</span>
                        <div className="flex-1 flex items-center">
                          <div
                            className={`${stage.color} h-9 rounded-md flex items-center justify-center transition-all duration-500`}
                            style={{ width: getWidth(stage.value) }}
                          >
                            <span className="text-xs font-bold text-white drop-shadow">{stage.value}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                    {metrics.rejected > 0 && (
                      <div className="flex items-center gap-4 mt-2">
                        <span className="text-xs text-slate-500 w-24 text-right shrink-0">Rejected</span>
                        <Badge variant="danger">{metrics.rejected}</Badge>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500 text-center py-8">No funnel data yet. Seed prospects and execute the campaign.</p>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === 'prospects' && (
          <Card>
            <CardHeader className="border-b border-slate-100">
              <CardTitle>Prospect List</CardTitle>
            </CardHeader>
            <div className="p-0">
              <ProspectTable campaignId={id} />
            </div>
          </Card>
        )}

        {activeTab === 'prompts' && (
          <PromptManager campaignId={id} />
        )}

        {activeTab === 'knowledge' && (
          <KnowledgeUpload campaignId={id} />
        )}

        {activeTab === 'logs' && (
          <AgentLogs campaignId={id} />
        )}
      </div>
    </>
  );
}
