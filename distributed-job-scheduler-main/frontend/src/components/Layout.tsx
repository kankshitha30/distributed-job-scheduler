import React from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Layers,
  Search,
  Cpu,
  BarChart3,
  Terminal,
  Zap,
} from 'lucide-react';
import { Navbar } from './Navbar';

interface LayoutProps {
  isPolling?: boolean;
  onTogglePolling?: () => void;
  onRefresh?: () => void;
  activeWorkers?: number;
}

export const Layout: React.FC<LayoutProps> = ({
  isPolling,
  onTogglePolling,
  onRefresh,
  activeWorkers,
}) => {
  const navItems = [
    { to: '/', label: 'Overview', icon: LayoutDashboard, exact: true },
    { to: '/queues', label: 'Queues', icon: Layers },
    { to: '/jobs', label: 'Job Explorer', icon: Search },
    { to: '/workers', label: 'Workers', icon: Cpu },
    { to: '/metrics', label: 'Metrics', icon: BarChart3 },
  ];

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-800 bg-slate-900/40 flex flex-col flex-shrink-0">
        {/* Brand */}
        <div className="h-16 flex items-center px-6 border-b border-slate-800 gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white tracking-wide">AGY Scheduler</h1>
            <p className="text-[10px] text-sky-400 font-mono">DISTRIBUTED V1.0</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-1.5 flex-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.exact}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-sky-600 text-white shadow-md shadow-sky-600/30 font-semibold'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`
                }
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Footer info */}
        <div className="p-4 border-t border-slate-800/80 bg-slate-900/60 text-xs text-slate-500">
          <div className="flex items-center gap-2 mb-1 text-slate-400 font-medium">
            <Terminal className="w-3.5 h-3.5 text-sky-400" />
            <span>PostgreSQL MVCC</span>
          </div>
          <p className="text-[11px] text-slate-500">Row-locking FOR UPDATE SKIP LOCKED</p>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Navbar
          isPolling={isPolling}
          onTogglePolling={onTogglePolling}
          onRefresh={onRefresh}
          activeWorkers={activeWorkers}
        />
        <main className="flex-1 overflow-y-auto p-6 md:p-8 bg-slate-950">
          <div className="max-w-7xl mx-auto space-y-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
