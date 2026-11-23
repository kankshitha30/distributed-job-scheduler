import React from 'react';
import { RefreshCw, User, LogOut, Activity, Cpu } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

interface NavbarProps {
  isPolling?: boolean;
  onTogglePolling?: () => void;
  onRefresh?: () => void;
  activeWorkers?: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  isPolling = true,
  onTogglePolling,
  onRefresh,
  activeWorkers = 0,
}) => {
  const { user, logout } = useAuth();

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/50 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/80 border border-slate-700/60 text-xs">
          <Cpu className={`w-3.5 h-3.5 ${activeWorkers > 0 ? 'text-emerald-400 animate-pulse' : 'text-slate-500'}`} />
          <span className="text-slate-300 font-medium">
            <strong className="text-white">{activeWorkers}</strong> Worker{activeWorkers === 1 ? '' : 's'} Online
          </span>
        </div>

        {onTogglePolling && (
          <button
            onClick={onTogglePolling}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
              isPolling
                ? 'bg-sky-950/60 border-sky-800/60 text-sky-300 hover:bg-sky-900/60'
                : 'bg-slate-800/60 border-slate-700/60 text-slate-400 hover:bg-slate-800'
            }`}
          >
            <Activity className={`w-3.5 h-3.5 ${isPolling ? 'animate-pulse text-sky-400' : 'text-slate-500'}`} />
            Live Polling: {isPolling ? '5s' : 'Paused'}
          </button>
        )}

        {onRefresh && (
          <button
            onClick={onRefresh}
            title="Refresh now"
            className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        )}
      </div>

      <div className="flex items-center gap-4">
        {user && (
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-sm text-slate-300">
              <div className="w-8 h-8 rounded-full bg-sky-600/20 border border-sky-500/30 flex items-center justify-center text-sky-400 font-semibold">
                {user.name.charAt(0).toUpperCase()}
              </div>
              <div className="hidden md:block text-left">
                <p className="text-xs font-medium text-white leading-tight">{user.name}</p>
                <p className="text-[11px] text-slate-400 leading-tight">{user.email}</p>
              </div>
            </div>

            <button
              onClick={logout}
              title="Logout"
              className="p-2 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-950/30 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
