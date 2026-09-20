import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
});

// No auth needed — backend bypasses JWT for demo
export const campaignsService = {
  getAll: () => api.get('/api/campaigns/').then(res => res.data),
  create: (data) => api.post('/api/campaigns/', data).then(res => res.data),
  update: (id, data) => api.patch(`/api/campaigns/${id}`, data).then(res => res.data),
  getLogs: (id, params) => api.get(`/api/campaigns/${id}/logs`, { params }).then(res => res.data),
  getMetrics: (id) => api.get(`/api/campaigns/${id}/metrics`).then(res => res.data),
  execute: (id) => api.post(`/api/campaigns/${id}/execute`).then(res => res.data),
  discover: (id) => api.post(`/api/campaigns/${id}/discover`).then(res => res.data),
  seedProspects: (id) => api.post(`/api/campaigns/${id}/seed`).then(res => res.data),
  uploadKnowledge: (id, data) => api.post(`/api/campaigns/${id}/knowledge`, data).then(res => res.data),
  getKnowledge: (id) => api.get(`/api/campaigns/${id}/knowledge`).then(res => res.data),
  getPrompts: (id) => api.get(`/api/campaigns/${id}/prompts`).then(res => res.data),
  createPrompt: (id, data) => api.post(`/api/campaigns/${id}/prompts`, data).then(res => res.data),
};

export const prospectsService = {
  getByCampaign: (campaignId, params) => api.get(`/api/prospects/${campaignId}`, { params }).then(res => res.data),
  update: (prospectId, data) => api.put(`/api/prospects/${prospectId}`, data).then(res => res.data),
  getFunnel: (campaignId) => api.get(`/api/prospects/${campaignId}/funnel`).then(res => res.data),
};

export const systemService = {
  getReps: () => api.get('/api/reps').then(res => res.data),
};

export const authService = {
  login: (email, password) => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    return api.post('/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    }).then(res => res.data);
  },
  getMe: () => api.get('/users/me').then(res => res.data)
};

export default api;
