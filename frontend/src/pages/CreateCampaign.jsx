import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import Header from '../components/layout/Header';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { campaignsService } from '../lib/api';
import { ArrowLeft } from 'lucide-react';

export default function CreateCampaign() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const [formData, setFormData] = useState({
    name: '',
    // Targeting Criteria
    roles: '',
    geography: '',
    industry: '',
    companySize: '',
    // Config
    isEmailEnabled: true,
    isLinkedinEnabled: true,
    isVoiceEnabled: false,
    isFollowUpEnabled: true,
    isResearchEnabled: true,
    dailyLimit: 50,
    repName: '',
    repEmail: '',
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const payload = {
        name: formData.name,
        targeting_criteria: {
          roles: formData.roles.split(',').map(r => r.trim()).filter(Boolean),
          geography: formData.geography,
          industry: formData.industry,
          company_size: formData.companySize,
        },
        config: {
          is_email_enabled: formData.isEmailEnabled,
          is_linkedin_enabled: formData.isLinkedinEnabled,
          is_voice_enabled: formData.isVoiceEnabled,
          is_follow_up_enabled: formData.isFollowUpEnabled,
          is_research_enabled: formData.isResearchEnabled,
          daily_limit: Number(formData.dailyLimit),
          assigned_rep: formData.repName
            ? { name: formData.repName, email: formData.repEmail }
            : null,
        },
      };

      const newCampaign = await campaignsService.create(payload);
      navigate(`/campaigns/${newCampaign.id}`);
    } catch (error) {
      console.error('Failed to create campaign', error);
      alert('Failed to create campaign. Check console for details.');
    } finally {
      setLoading(false);
    }
  };

  const update = (key, value) => setFormData(prev => ({ ...prev, [key]: value }));

  return (
    <>
      <Header
        title={
          <div className="flex items-center space-x-3">
            <Link to="/dashboard" className="text-slate-400 hover:text-slate-600">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <span>Create New Campaign</span>
          </div>
        }
      />

      <div className="max-w-3xl mx-auto mt-8 space-y-6">
        {/* Info Banner */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800">
          <strong>Workflow:</strong> Campaigns are created in <strong>Draft</strong> status.
          After creating, go to the campaign detail page to → <strong>Set Live</strong> → <strong>Seed Prospects</strong> → <strong>Execute AI Agents</strong>.
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Section 1: Basic Info */}
          <Card>
            <CardContent className="p-8 space-y-5">
              <h2 className="text-lg font-semibold text-slate-900 border-b border-slate-100 pb-3">Basic Info</h2>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Campaign Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={e => update('name', e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
                  placeholder="e.g. US SaaS CTO Outbound"
                  required
                />
              </div>
            </CardContent>
          </Card>

          {/* Section 2: ICP & Audience */}
          <Card>
            <CardContent className="p-8 space-y-5">
              <h2 className="text-lg font-semibold text-slate-900 border-b border-slate-100 pb-3">ICP & Audience</h2>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Target Roles (comma separated)</label>
                <input
                  type="text"
                  value={formData.roles}
                  onChange={e => update('roles', e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
                  placeholder="e.g. CTO, VP of Engineering, Head of IT"
                />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">Geography</label>
                  <input
                    type="text"
                    value={formData.geography}
                    onChange={e => update('geography', e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
                    placeholder="e.g. United States"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">Industry</label>
                  <input
                    type="text"
                    value={formData.industry}
                    onChange={e => update('industry', e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
                    placeholder="e.g. B2B SaaS"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">Company Size</label>
                  <select
                    value={formData.companySize}
                    onChange={e => update('companySize', e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none bg-white"
                  >
                    <option value="">Select size...</option>
                    <option value="1-50">1–50 employees</option>
                    <option value="50-200">50–200 employees</option>
                    <option value="50-500">50–500 employees</option>
                    <option value="200-1000">200–1000 employees</option>
                    <option value="500+">500+ employees</option>
                    <option value="1000+">1000+ employees</option>
                  </select>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Section 3: Channels & Config */}
          <Card>
            <CardContent className="p-8 space-y-5">
              <h2 className="text-lg font-semibold text-slate-900 border-b border-slate-100 pb-3">Channels & Config</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {[
                  { key: 'isEmailEnabled', label: 'Email Outreach' },
                  { key: 'isLinkedinEnabled', label: 'LinkedIn Outreach' },
                  { key: 'isVoiceEnabled', label: 'Voice Calls' },
                  { key: 'isFollowUpEnabled', label: 'Auto Follow-Up' },
                  { key: 'isResearchEnabled', label: 'AI Research' },
                ].map(ch => (
                  <label key={ch.key} className="flex items-center space-x-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData[ch.key]}
                      onChange={e => update(ch.key, e.target.checked)}
                      className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                    />
                    <span className="text-sm text-slate-700">{ch.label}</span>
                  </label>
                ))}
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Daily Outreach Limit</label>
                <input
                  type="number"
                  value={formData.dailyLimit}
                  onChange={e => update('dailyLimit', e.target.value)}
                  className="w-32 border border-slate-300 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
                  min={1}
                  max={500}
                />
              </div>
            </CardContent>
          </Card>

          {/* Section 4: Assigned Rep */}
          <Card>
            <CardContent className="p-8 space-y-5">
              <h2 className="text-lg font-semibold text-slate-900 border-b border-slate-100 pb-3">Assigned Sales Rep</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">Rep Name</label>
                  <input
                    type="text"
                    value={formData.repName}
                    onChange={e => update('repName', e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
                    placeholder="e.g. Alex Miller"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">Rep Email</label>
                  <input
                    type="email"
                    value={formData.repEmail}
                    onChange={e => update('repEmail', e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
                    placeholder="e.g. alex@company.com"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Submit */}
          <div className="flex justify-end space-x-3 pb-8">
            <Link to="/dashboard">
              <Button type="button" variant="ghost">Cancel</Button>
            </Link>
            <Button type="submit" size="lg" disabled={loading}>
              {loading ? 'Creating...' : 'Create Campaign (Draft)'}
            </Button>
          </div>
        </form>
      </div>
    </>
  );
}
