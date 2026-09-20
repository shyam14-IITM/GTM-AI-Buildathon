import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './components/layout/MainLayout';
import Dashboard from './pages/Dashboard';
import CampaignDetail from './pages/CampaignDetail';
import CreateCampaign from './pages/CreateCampaign';
import Login from './pages/Login';

const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem('sdr_token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="campaigns/new" element={<CreateCampaign />} />
          <Route path="campaigns/:id" element={<CampaignDetail />} />
          <Route path="prospects" element={<div className="p-8 text-slate-600 font-medium">Prospects (Coming Soon)</div>} />
          <Route path="conversations" element={<div className="p-8 text-slate-600 font-medium">Conversations (Coming Soon)</div>} />
          <Route path="analytics" element={<div className="p-8 text-slate-600 font-medium">Analytics (Coming Soon)</div>} />
          <Route path="knowledge" element={<div className="p-8 text-slate-600 font-medium">Knowledge Base (Coming Soon)</div>} />
          <Route path="settings" element={<div className="p-8 text-slate-600 font-medium">Settings (Coming Soon)</div>} />
          {/* Fallback */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
