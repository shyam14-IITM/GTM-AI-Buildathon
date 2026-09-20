import React, { useEffect, useState } from 'react';
import Header from '../components/layout/Header';
import { MetricCard } from '../components/ui/MetricCard';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import CampaignRow from '../components/CampaignRow';
import { Link } from 'react-router-dom';
import { Users, UserCheck, MessageSquare, Calendar } from 'lucide-react';
import { campaignsService } from '../lib/api';

export default function Dashboard() {
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCampaigns();
  }, []);

  const fetchCampaigns = async () => {
    try {
      const data = await campaignsService.getAll();
      setCampaigns(data);
    } catch (error) {
      console.error("Failed to fetch campaigns", error);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleStatus = async (id, newStatus) => {
    try {
      await campaignsService.update(id, { status: newStatus });
      setCampaigns(prev => prev.map(c => c.id === id ? { ...c, status: newStatus } : c));
    } catch (error) {
      console.error("Failed to update status", error);
      // Fallback update for visual testing
      setCampaigns(prev => prev.map(c => c.id === id ? { ...c, status: newStatus } : c));
    }
  };

  return (
    <>
      <Header title="Overview" />
      <div className="max-w-7xl mx-auto space-y-6 mt-6">
        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <MetricCard title="Total Campaigns" value={campaigns.length} change="12" icon={Users} />
          <MetricCard title="Active Campaigns" value={campaigns.filter(c => c.status === 'Live').length} change="18" icon={UserCheck} />
          <MetricCard title="Replies" value="248" change="22" icon={MessageSquare} />
          <MetricCard title="Meetings" value="72" change="16" icon={Calendar} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Campaign List */}
          <Card className="lg:col-span-2">
            <CardHeader className="border-b border-slate-100 flex flex-row items-center justify-between">
              <CardTitle>Campaign Status</CardTitle>
              <Link to="/campaigns/new">
                <Button size="sm" variant="primary">Create Campaign</Button>
              </Link>
            </CardHeader>
            <CardContent className="p-0">
              {loading ? (
                <div className="p-8 text-center text-slate-500">Loading campaigns...</div>
              ) : campaigns.length === 0 ? (
                <div className="p-8 text-center text-slate-500">No campaigns found.</div>
              ) : (
                <div className="flex flex-col">
                  {campaigns.map(campaign => (
                    <CampaignRow key={campaign.id} campaign={campaign} onToggleStatus={handleToggleStatus} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Placeholder for Analytics Graph */}
          <Card>
            <CardHeader className="border-b border-slate-100">
              <CardTitle>Recent Activity</CardTitle>
            </CardHeader>
            <CardContent className="p-6 text-sm text-slate-600">
              <div className="space-y-4">
                <div className="flex space-x-3">
                  <div className="w-2 h-2 mt-1.5 rounded-full bg-primary-500"></div>
                  <div>
                    <p className="font-medium text-slate-900">Email sent to Sarah Kim</p>
                    <p className="text-xs text-slate-500">2 hours ago • SaaS - US Founders</p>
                  </div>
                </div>
                <div className="flex space-x-3">
                  <div className="w-2 h-2 mt-1.5 rounded-full bg-green-500"></div>
                  <div>
                    <p className="font-medium text-slate-900">Meeting booked with TechLabs</p>
                    <p className="text-xs text-slate-500">5 hours ago • SaaS - US Founders</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}
