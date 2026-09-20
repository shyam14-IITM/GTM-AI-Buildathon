import React, { useState, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Users, MessageSquare, BarChart2, Book, Settings, LogOut } from 'lucide-react';
import { cn } from '../../lib/utils';
import { authService } from '../../lib/api';

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard', href: '/dashboard' },
  { icon: Users, label: 'Prospects', href: '/prospects' },
  { icon: MessageSquare, label: 'Conversations', href: '/conversations' },
  { icon: BarChart2, label: 'Analytics', href: '/analytics' },
  { icon: Book, label: 'Knowledge Base', href: '/knowledge' },
  { icon: Settings, label: 'Settings', href: '/settings' },
];

export default function Sidebar() {
  const [user, setUser] = useState({ name: 'Loading...', email: '' });
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('sdr_token');
    navigate('/login');
  };

  useEffect(() => {
    authService.getMe()
      .then(data => {
        if (data) setUser(data);
      })
      .catch(err => {
        console.error("Failed to fetch user", err);
        setUser({ name: 'Unknown User', email: 'unknown@company.com' });
      });
  }, []);

  const initials = user.name
    .split(' ')
    .filter(n => n.length > 0)
    .map(n => n[0])
    .join('')
    .substring(0, 2)
    .toUpperCase() || '??';

  return (
    <aside className="w-64 bg-sidebar border-r border-slate-200 h-screen flex flex-col fixed left-0 top-0">
      <div className="p-6 flex items-center space-x-3">
        <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
          <span className="text-white font-bold text-lg">AI</span>
        </div>
        <span className="text-xl font-bold text-slate-900">SDR</span>
      </div>
      
      <nav className="flex-1 px-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.href}
              to={item.href}
              className={({ isActive }) => cn(
                "flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                isActive 
                  ? "bg-primary-50 text-primary-700" 
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              )}
            >
              <Icon className="w-5 h-5" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
      
      <div className="p-4 border-t border-slate-200">
        <div className="flex items-center space-x-3 px-3 py-2">
          <div className="w-8 h-8 rounded-full bg-slate-300 flex items-center justify-center text-slate-600 font-bold shrink-0">
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-900 truncate">{user.name}</p>
            <p className="text-xs text-slate-500 truncate">{user.email}</p>
          </div>
          <button 
            onClick={handleLogout}
            className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
            title="Log out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
