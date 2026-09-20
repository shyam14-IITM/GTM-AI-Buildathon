import React from 'react';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { Play, Pause, MoreVertical } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function CampaignRow({ campaign, onToggleStatus }) {
  const isLive = campaign.status === 'Live';
  
  return (
    <div className="flex items-center justify-between p-4 border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors">
      <div className="flex-1 min-w-0 pr-4">
        <div className="flex items-center space-x-3 mb-1">
          <Link to={`/campaigns/${campaign.id}`} className="text-sm font-medium text-slate-900 hover:text-primary-600 hover:underline truncate">
            {campaign.name}
          </Link>
          <Badge variant={isLive ? 'success' : campaign.status === 'Paused' ? 'warning' : 'default'}>
            <span className="w-1.5 h-1.5 rounded-full bg-current mr-1.5 inline-block"></span>
            {campaign.status}
          </Badge>
        </div>
        <p className="text-xs text-slate-500 truncate">
          {campaign.config?.target_roles || 'Various Roles'} • {campaign.targeting_criteria?.company_size || 'All Sizes'}
        </p>
      </div>
      
      <div className="flex items-center space-x-4">
        <Button 
          variant="ghost" 
          size="sm"
          onClick={() => onToggleStatus(campaign.id, isLive ? 'Paused' : 'Live')}
          className={isLive ? "text-amber-600 hover:text-amber-700 hover:bg-amber-50" : "text-green-600 hover:text-green-700 hover:bg-green-50"}
        >
          {isLive ? <Pause className="w-4 h-4 mr-1.5" /> : <Play className="w-4 h-4 mr-1.5" />}
          {isLive ? 'Pause' : 'Resume'}
        </Button>
        <Link to={`/campaigns/${campaign.id}`}>
          <Button variant="secondary" size="sm">
            View Details
          </Button>
        </Link>
      </div>
    </div>
  );
}
