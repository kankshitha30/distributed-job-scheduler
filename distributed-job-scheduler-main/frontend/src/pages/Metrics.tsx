import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  Clock,
  CheckCircle2,
  XCircle,
  AlertOctagon,
  BarChart3,
  PieChart,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { OverviewMetrics } from '../types';
import { api } from '../services/api';
import { usePolling } from '../hooks/usePolling';

export const Metrics: React.FC = () => {
  const [metrics, setMetrics] = useState<OverviewMetrics | null>(null);

  const fetchMetrics = async () => {
    try {
      const data = await api.getMetricsOverview();
      setMetrics(data);
    } catch (e) {
      console.error('Failed to load metrics', e);
    }
  };

  usePolling(fetchMetrics, 4000);

  const jobTypeData = metrics?.job_type_distribution
    ? Object.entries(metrics.job_type_distribution).map(([name, value]) => ({
        name,
        count: value,
      }))
    : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="pb-2 border-b border-slate-800">
        <h2 className="text-2xl font-bold text-white tracking-tight">System Metrics & Analytics</h2>
        <p className="text-sm text-slate-400">
          Telemetry insights into execution latencies, throughput rates, and queue health trends.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Throughput</span>
            <TrendingUp className="w-4 h-4 text-sky-400" />
          </div>
          <p className="text-2xl font-bold text-white font-mono">
            {metrics?.throughput_per_minute || 0}{' '}
            <span className="text-xs font-normal text-slate-400">jobs/min</span>
          </p>
          <p className="text-[11px] text-slate-500 mt-1">Calculated over rolling window</p>
        </div>

        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Success Rate</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-emerald-400 font-mono">
            {metrics?.success_rate || 100}%
          </p>
          <p className="text-[11px] text-slate-500 mt-1">Completed vs Failed/DLQ ratio</p>
        </div>

        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Average Execution Time</span>
            <Clock className="w-4 h-4 text-purple-400" />
          </div>
          <p className="text-2xl font-bold text-slate-100 font-mono">
            {metrics?.average_duration_ms || 0}{' '}
            <span className="text-xs font-normal text-slate-400">ms</span>
          </p>
          <p className="text-[11px] text-slate-500 mt-1">Mean duration of finished tasks</p>
        </div>

        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Dead Letter Queue</span>
            <AlertOctagon className="w-4 h-4 text-rose-400" />
          </div>
          <p className="text-2xl font-bold text-rose-400 font-mono">
            {metrics?.dead_letter_jobs || 0}
          </p>
          <p className="text-[11px] text-slate-500 mt-1">Permanently failed after retries</p>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: Time Series Activity */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-semibold text-white">Execution Trend</h3>
              <p className="text-xs text-slate-400">Completed vs Failed job executions</p>
            </div>
            <BarChart3 className="w-5 h-5 text-sky-400" />
          </div>

          <div className="h-64 w-full">
            {metrics?.time_series && metrics.time_series.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={metrics.time_series} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="areaCompleted" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                    </linearGradient>
                    <linearGradient id="areaFailed" x1="0" y1="0" x2="0" y2="1">
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
                  <Legend wrapperStyle={{ fontSize: '12px' }} />
                  <Area type="monotone" name="Completed" dataKey="completed" stroke="#10b981" fillOpacity={1} fill="url(#areaCompleted)" strokeWidth={2} />
                  <Area type="monotone" name="Failed" dataKey="failed" stroke="#ef4444" fillOpacity={1} fill="url(#areaFailed)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-500 text-sm">
                No telemetry available yet
              </div>
            )}
          </div>
        </div>

        {/* Chart 2: Incoming Queued Workload */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-semibold text-white">Incoming Workload</h3>
              <p className="text-xs text-slate-400">Newly enqueued tasks per time window</p>
            </div>
            <TrendingUp className="w-5 h-5 text-indigo-400" />
          </div>

          <div className="h-64 w-full">
            {metrics?.time_series && metrics.time_series.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={metrics.time_series} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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
                  <Bar name="Queued" dataKey="queued" fill="#38bdf8" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-500 text-sm">
                No incoming workload logged
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Job Type Breakdown */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
        <h3 className="text-base font-semibold text-white mb-1">Job Handler Breakdown</h3>
        <p className="text-xs text-slate-400 mb-4">Distribution of tasks categorized by executor type</p>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
          {jobTypeData.map((item) => (
            <div key={item.name} className="bg-slate-950/70 border border-slate-800 rounded-xl p-4">
              <span className="text-xs font-mono text-slate-400 uppercase">{item.name}</span>
              <p className="text-xl font-bold text-white mt-1 font-mono">{item.count}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
