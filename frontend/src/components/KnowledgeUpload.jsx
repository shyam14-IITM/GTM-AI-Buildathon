import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { Button } from './ui/Button';
import { campaignsService } from '../lib/api';
import { Upload, FileText, CheckCircle } from 'lucide-react';

export default function KnowledgeUpload({ campaignId }) {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [docs, setDocs] = useState([]);

  const fetchDocs = async () => {
    try {
      const data = await campaignsService.getKnowledge(campaignId);
      setDocs(data);
    } catch (err) {
      console.error('Failed to fetch knowledge docs', err);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, [campaignId]);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!content.trim()) return;
    
    setLoading(true);
    setResult(null);
    try {
      const data = await campaignsService.uploadKnowledge(campaignId, {
        title: title || 'Knowledge Context',
        content: content
      });
      setResult(data.message);
      setTitle('');
      setContent('');
      fetchDocs();
    } catch (err) {
      console.error('Failed to upload knowledge', err);
      setResult('Upload failed. Check console.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader className="border-b border-slate-100">
        <div className="flex items-center space-x-2">
          <FileText className="w-5 h-5 text-primary-600" />
          <CardTitle>Knowledge Base (RAG)</CardTitle>
        </div>
        <p className="text-sm text-slate-500 mt-1">
          Upload product info, ICPs, playbooks, or case studies. Used by agents for contextual responses.
        </p>
      </CardHeader>
      <CardContent className="p-6">
        <form onSubmit={handleUpload} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Document Title</label>
            <input
              type="text"
              value={title}
              onChange={e => setTitle(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
              placeholder="e.g. Core Value Proposition, Objection Handler"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Content *</label>
            <textarea
              value={content}
              onChange={e => setContent(e.target.value)}
              rows={6}
              className="w-full border border-slate-300 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none resize-y"
              placeholder="Paste your product description, case study, objection handling playbook..."
              required
            />
          </div>
          <div className="flex items-center justify-between">
            <div>
              {result && (
                <div className="flex items-center space-x-2 text-sm text-green-600">
                  <CheckCircle className="w-4 h-4" />
                  <span>{result}</span>
                </div>
              )}
            </div>
            <Button type="submit" disabled={loading}>
              <Upload className="w-4 h-4 mr-2" />
              {loading ? 'Embedding...' : 'Upload & Embed'}
            </Button>
          </div>
        </form>
      </CardContent>
      
      {docs.length > 0 && (
        <div className="border-t border-slate-100 p-6 bg-slate-50">
          <h3 className="text-sm font-semibold text-slate-900 mb-4">Currently Active Knowledge</h3>
          <div className="space-y-3">
            {docs.map((doc, idx) => (
              <div key={idx} className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
                <h4 className="font-medium text-slate-800 mb-1">{doc.title}</h4>
                <p className="text-sm text-slate-500 whitespace-pre-wrap">{doc.preview}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
