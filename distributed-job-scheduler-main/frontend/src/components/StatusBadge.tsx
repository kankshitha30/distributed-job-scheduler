import React from 'react';
import { JobStatus, WorkerStatus } from '../types';

interface StatusBadgeProps {
  status: JobStatus | WorkerStatus | string;
  size?: 'sm' | 'md' | 'lg';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'sm' }) => {
  const sizeClasses = {
    sm: 'text-xs px-2.5 py-0.5',
    md: 'text-sm px-3 py-1',
    lg: 'text-base px-3.5 py-1.5',
  }[size];

  switch (status) {
    // Job Statuses
    case 'QUEUED':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full font-medium bg-slate-800 text-slate-300 border border-slate-700 ${sizeClasses}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
          QUEUED
        </span>
      );
    case 'SCHEDULED':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full font-medium bg-purple-950/70 text-purple-300 border border-purple-800/60 ${sizeClasses}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-purple-400"></span>
          SCHEDULED
        </span>
      );
    case 'CLAIMED':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full font-medium bg-amber-950/70 text-amber-300 border border-amber-800/60 ${sizeClasses}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
          CLAIMED
        </span>
      );
    case 'RUNNING':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full font-medium bg-sky-950/70 text-sky-300 border border-sky-800/60 ${sizeClasses}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-ping"></span>
          RUNNING
        </span>
      );
    case 'COMPLETED':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full font-medium bg-emerald-950/70 text-emerald-300 border border-emerald-800/60 ${sizeClasses}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          COMPLETED
        </span>
      );
    case 'FAILED':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full font-medium bg-red-950/70 text-red-300 border border-red-800/60 ${sizeClasses}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-red-400"></span>
          FAILED
        </span>
      );
    case 'RETRYING':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full font-medium bg-orange-950/70 text-orange-300 border border-orange-800/60 ${sizeClasses}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-orange-400 animate-pulse"></span>
          RETRYING
        </span>
      );
    case 'DEAD_LETTER':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full font-medium bg-rose-950/80 text-rose-200 border border-rose-800 ${sizeClasses}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
          DEAD LETTER
        </span>
      );

    // Worker Statuses
    case 'ONLINE':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full font-medium bg-emerald-950/80 text-emerald-300 border border-emerald-700/60 ${sizeClasses}`}>
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          ONLINE
        </span>
      );
    case 'OFFLINE':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full font-medium bg-slate-900 text-slate-400 border border-slate-800 ${sizeClasses}`}>
          <span className="w-2 h-2 rounded-full bg-slate-500"></span>
          OFFLINE
        </span>
      );
    case 'STOPPING':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full font-medium bg-yellow-950/70 text-yellow-300 border border-yellow-800/60 ${sizeClasses}`}>
          <span className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse"></span>
          STOPPING
        </span>
      );

    default:
      return (
        <span className={`inline-flex items-center gap-1 rounded-full font-medium bg-slate-800 text-slate-300 ${sizeClasses}`}>
          {status}
        </span>
      );
  }
};
