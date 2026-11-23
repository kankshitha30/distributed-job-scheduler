import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Layers,
  CheckCircle2,
  XCircle,
  AlertOctagon,
  Cpu,
  TrendingUp,
  Activity,
  Plus,
  Play,
  Pause,
  ArrowUpRight,
  Clock,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

import { OverviewMetrics, Queue } from '../types';
import { api } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';
import { JobCreateModal } from '../components/JobCreateModal';
import { QueueCreateModal } from '../components/QueueCreateModal';

interface DashboardProps {
  metrics: OverviewMetrics | null;
  queues: Queue[];
  onRefresh: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  metrics,
  queues,
  onRefresh,
}) => {
  const [isJobModalOpen, setIsJobModalOpen] = useState(false);
  const [isQueueModalOpen, setIsQueueModalOpen] = useState(false);
  const [projects, setProjects] = useState<any[]>([]);

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const pList = await api.getProjects();
        setProjects(pList);
      } catch (e) {
        console.error('Failed to load projects', e);
      }
    };
    fetchProjects();
  }, []);

  const handleTogglePause = async (queue: Queue) => {
    try {
      if (queue.paused) {
        await api.resumeQueue(queue.id);
      } else {
        await api.pauseQueue(queue.id);
      }
      onRefresh();
    } catch (e) {
      console.error('Failed to toggle queue pause', e);
    }
  };

  const statCards = [
    {
      title: 'Total Queues',
      value: metrics?.total_queues || 0,
      icon: Layers,
      color: 'text-sky-400',
      bg: 'bg-sky-500/10 border-sky-500/20',
      link: '/queues',
    },
    {
      title: 'Active Workers',
      value: `${metrics?.active_workers || 0} / ${metrics?.total_workers || 0}`,
      icon: Cpu,
      color: 'text-emerald-400',
      bg: 'bg-emerald-500/10 border-emerald-500/20',
      link: '/workers',
    },
    {
      title: 'Running Jobs',
      value: metrics?.running_jobs || 0,
      icon: Activity,
      color: 'text-amber-400',
      bg: 'bg-amber-500/10 border-amber-500/20',
      link: '/jobs?status=RUNNING',
    },
    {
      title: 'Completed',
      value: metrics?.completed_jobs || 0,
      icon: CheckCircle2,
      color: 'text-emerald-400',
      bg: 'bg-emerald-500/10 border-emerald-500/20',
      link: '/jobs?status=COMPLETED',
    },
    {
      title: 'Failed',
      value: metrics?.failed_jobs || 0,
      icon: XCircle,
      color: 'text-red-400',
      bg: 'bg-red-500/10 border-red-500/20',
      link: '/jobs?status=FAILED',
    },
    {
      title: 'Dead Letter Queue',
      value: metrics?.dead_letter_jobs || 0,
      icon: AlertOctagon,
      color: 'text-rose-400',
      bg: 'bg-rose-500/10 border-rose-500/20',
      link: '/jobs?status=DEAD_LETTER',
    },
  ];

  return (
    <div className="space-y-8">
      {/* Top Banner & Quick Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800/80">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">System Overview</h2>
          <p className="text-sm text-slate-400">
            Real-time telemetry and atomic distributed job dispatch statistics.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsQueueModalOpen(true)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
          >
            <Layers className="w-4 h-4" />
            New Queue
          </button>
          <button
            onClick={() => setIsJobModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-sky-600 hover:bg-sky-500 text-white shadow-lg shadow-sky-600/30 transition-all"
          >
            <Plus className="w-4 h-4" />
            Enqueue Job
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {statCards.map((card, idx) => {
          const Icon = card.icon;
          return (
            <Link
              key={idx}
              to={card.link}
              className={`p-4 rounded-xl border transition-all hover:scale-[1.02] ${card.bg}`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-slate-400">{card.title}</span>
                <Icon className={`w-4 h-4 ${card.color}`} />
              </div>
              <div className="text-xl font-bold text-white">{card.value}</div>
            </Link>
          );
        })}
      </div>

      {/* Throughput & Success Rate Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Throughput</p>
            <h4 className="text-2xl font-bold text-white mt-1">
              {metrics?.throughput_per_minute || 0}{' '}
              <span className="text-xs font-normal text-slate-400">jobs/min</span>
            </h4>
          </div>
          <div className="p-3 rounded-xl bg-sky-950/60 border border-sky-800/40 text-sky-400">
            <TrendingUp className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Success Rate</p>
            <h4 className="text-2xl font-bold text-emerald-400 mt-1">
              {metrics?.success_rate || 100}%
            </h4>
          </div>
          <div className="p-3 rounded-xl bg-emerald-950/60 border border-emerald-800/40 text-emerald-400">
            <CheckCircle2 className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Avg Duration</p>
            <h4 className="text-2xl font-bold text-slate-100 mt-1">
              {metrics?.average_duration_ms || 0}{' '}
              <span className="text-xs font-normal text-slate-400">ms</span>
            </h4>
          </div>
          <div className="p-3 rounded-xl bg-purple-950/60 border border-purple-800/40 text-purple-400">
            <Clock className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Chart: Activity Over Time */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-base font-semibold text-white">Execution Activity</h3>
            <p className="text-xs text-slate-400 mt-0.5">Completed and Failed jobs across recent time intervals</p>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full bg-emerald-500"></span>
              <span className="text-slate-300">Completed</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full bg-red-500"></span>
              <span className="text-slate-300">Failed</span>
            </div>
          </div>
        </div>

        <div className="h-64 w-full">
          {metrics?.time_series && metrics.time_series.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={metrics.time_series} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="completedGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="failedGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="timestamp" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    fontSize: '12px',
                    color: '#f8fafc',
                  }}
                />
                <Area type="monotone" dataKey="completed" stroke="#10b981" fillOpacity={1} fill="url(#completedGrad)" strokeWidth={2} />
                <Area type="monotone" dataKey="failed" stroke="#ef4444" fillOpacity={1} fill="url(#failedGrad)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-500 text-sm">
              No recent execution telemetry
            </div>
          )}
        </div>
      </div>

      {/* Queues Quick Overview */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-white">Active Queues</h3>
            <p className="text-xs text-slate-400">Current queue status and workload distribution</p>
          </div>
          <Link
            to="/queues"
            className="text-xs font-medium text-sky-400 hover:text-sky-300 flex items-center gap-1"
          >
            Manage All Queues <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-950/60 text-slate-400 text-xs uppercase font-semibold border-b border-slate-800">
              <tr>
                <th className="px-6 py-3.5">Queue Name</th>
                <th className="px-6 py-3.5">Status</th>
                <th className="px-6 py-3.5">Priority</th>
                <th className="px-6 py-3.5">Concurrency</th>
                <th className="px-6 py-3.5">Queued</th>
                <th className="px-6 py-3.5">Running</th>
                <th className="px-6 py-3.5">Success Rate</th>
                <th className="px-6 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {queues.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-6 py-8 text-center text-slate-500">
                    No queues configured. Click "New Queue" to create one.
                  </td>
                </tr>
              ) : (
                queues.map((q) => (
                  <tr key={q.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-6 py-4 font-semibold text-white">
                      <Link to={`/queues/${q.id}`} className="hover:text-sky-400 transition-colors">
                        {q.name}
                      </Link>
                    </td>
                    <td className="px-6 py-4">
                      {q.paused ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-950/70 text-amber-300 border border-amber-800">
                          Paused
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-950/70 text-emerald-300 border border-emerald-800">
                          Active
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 font-mono text-xs">{q.priority}</td>
                    <td className="px-6 py-4 font-mono text-xs">{q.concurrency_limit}</td>
                    <td className="px-6 py-4 font-medium text-slate-200">{q.stats?.queued_jobs || 0}</td>
                    <td className="px-6 py-4 font-medium text-sky-400">{q.stats?.running_jobs || 0}</td>
                    <td className="px-6 py-4 font-medium text-emerald-400">{q.stats?.success_rate || 100}%</td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => handleTogglePause(q)}
                        className={`p-1.5 rounded-lg border transition-colors ${
                          q.paused
                            ? 'bg-emerald-950/60 border-emerald-800 text-emerald-400 hover:bg-emerald-900/60'
                            : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
                        }`}
                        title={q.paused ? 'Resume Queue' : 'Pause Queue'}
                      >
                        {q.paused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modals */}
      <JobCreateModal
        isOpen={isJobModalOpen}
        onClose={() => setIsJobModalOpen(false)}
        queues={queues}
        onJobCreated={onRefresh}
      />
      <QueueCreateModal
        isOpen={isQueueModalOpen}
        onClose={() => setIsQueueModalOpen(false)}
        projects={projects}
        onQueueCreated={onRefresh}
      />
    </div>
  );
};
