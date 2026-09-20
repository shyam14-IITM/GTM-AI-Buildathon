import React, { useEffect, useState } from 'react';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { campaignsService } from '../lib/api';
import { ScrollText, AlertTriangle, CheckCircle, XCircle, RefreshCw } from 'lucide-react';

const JsonViewer = ({ data }) => {
  if (typeof data !== 'object' || data === null) return <span>{String(data)}</span>;
  
  return (
    <div className="mt-3 space-y-1.5 bg-slate-50 border border-slate-200 rounded-lg p-3">
      {Object.entries(data).map(([key, value]) => (
        <div key={key} className="text-xs">
          <span className="font-semibold text-slate-700 capitalize mr-2">
            {key.replace(/_/g, ' ')}:
          </span>
          {typeof value === 'object' && value !== null ? (
            <div className="pl-4 border-l-2 border-primary-200 mt-1.5 py-1">
              <JsonViewer data={value} />
            </div>
          ) : (
            <span className="text-slate-600 whitespace-pre-wrap leading-relaxed">{String(value)}</span>
          )}
        </div>
      ))}
    </div>
  );
};

export default function AgentLogs({ campaignId }) {
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const limit = 20;

  useEffect(() => {
    fetchLogs();
  }, [campaignId, page]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const data = await campaignsService.getLogs(campaignId, { skip: page * limit, limit });
      setLogs(data.data || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error('Failed to fetch logs', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    if (status === 'SUCCESS') return <CheckCircle className="w-4 h-4 text-green-500" />;
    if (status === 'ERROR') return <XCircle className="w-4 h-4 text-red-500" />;
    return <AlertTriangle className="w-4 h-4 text-amber-500" />;
  };

  const getStatusVariant = (status) => {
    if (status === 'SUCCESS') return 'success';
    if (status === 'ERROR') return 'danger';
    return 'warning';
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between border-b border-slate-100">
        <div className="flex items-center space-x-2">
          <ScrollText className="w-5 h-5 text-primary-600" />
          <CardTitle>Agent Activity Log</CardTitle>
        </div>
        <Button variant="ghost" size="sm" onClick={fetchLogs}>
          <RefreshCw className="w-4 h-4 mr-1.5" /> Refresh
        </Button>
      </CardHeader>
      <CardContent className="p-0">
        {loading ? (
          <div className="p-8 text-center text-slate-500">Loading agent logs...</div>
        ) : logs.length === 0 ? (
          <div className="p-8 text-center text-slate-500">
            No agent activity recorded yet. Execute the campaign to generate logs.
          </div>
        ) : (
          <>
            <div className="divide-y divide-slate-100">
              {logs.map((log) => (
                <div key={log.id} className="px-6 py-4 hover:bg-slate-50 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-3">
                      {getStatusIcon(log.status)}
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="text-sm font-semibold text-slate-900">{log.agent_name}</span>
                          <Badge variant={getStatusVariant(log.status)}>{log.status}</Badge>
                          {log.action === 'ESCALATED' && (
                            <Badge variant="danger">⚠ Escalated</Badge>
                          )}
                        </div>
                        <p className="text-sm text-slate-600 mt-0.5">{log.action}</p>
                        {log.details && Object.keys(log.details).length > 0 && (
                          <div className="max-w-2xl overflow-x-auto">
                            <JsonViewer data={log.details} />
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="text-right shrink-0 ml-4">
                      <p className="text-xs text-slate-400">
                        {new Date(log.created_at).toLocaleString()}
                      </p>
                      <p className="text-xs text-slate-400 mt-0.5">v{log.prompt_version}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
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
          </>
        )}
      </CardContent>
    </Card>
  );
}
