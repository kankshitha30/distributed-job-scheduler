import React, { useState, useEffect } from 'react';
import {
  Cpu,
  Activity,
  Server,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Radio,
  History,
} from 'lucide-react';
import { Worker, WorkerHeartbeat } from '../types';
import { api } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';
import { Modal } from '../components/Modal';
import { usePolling } from '../hooks/usePolling';

export const Workers: React.FC = () => {
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [selectedWorkerId, setSelectedWorkerId] = useState<string | null>(null);
  const [heartbeats, setHeartbeats] = useState<WorkerHeartbeat[]>([]);
  const [isHbModalOpen, setIsHbModalOpen] = useState(false);

  const fetchWorkers = async () => {
    try {
      const data = await api.getWorkers();
      setWorkers(data);
    } catch (e) {
      console.error('Failed to load workers', e);
    }
  };

  usePolling(fetchWorkers, 4000);

  const handleViewHeartbeats = async (workerId: string) => {
    setSelectedWorkerId(workerId);
    try {
      const hbList = await api.getWorkerHeartbeats(workerId, 30);
      setHeartbeats(hbList);
      setIsHbModalOpen(true);
    } catch (e) {
      console.error('Failed to load heartbeats', e);
    }
  };

  const activeWorkersCount = workers.filter((w) => w.status === 'ONLINE').length;
  const totalSlots = workers
    .filter((w) => w.status === 'ONLINE')
    .reduce((acc, w) => acc + w.concurrency, 0);
  const totalActiveJobs = workers
    .filter((w) => w.status === 'ONLINE')
    .reduce((acc, w) => acc + w.active_jobs, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Worker Fleet</h2>
          <p className="text-sm text-slate-400">
            Monitor distributed worker node registrations, concurrent asyncio task pools, and heartbeat telemetry.
          </p>
        </div>
      </div>

      {/* Fleet Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">Active Nodes</span>
            <p className="text-2xl font-bold text-emerald-400 mt-1">
              {activeWorkersCount}{' '}
              <span className="text-xs font-normal text-slate-400">/ {workers.length} total</span>
            </p>
          </div>
          <div className="p-3 rounded-xl bg-emerald-950/60 border border-emerald-800/40 text-emerald-400">
            <Radio className="w-6 h-6 animate-pulse" />
          </div>
        </div>

        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">Running Concurrent Jobs</span>
            <p className="text-2xl font-bold text-sky-400 mt-1">
              {totalActiveJobs}
            </p>
          </div>
          <div className="p-3 rounded-xl bg-sky-950/60 border border-sky-800/40 text-sky-400">
            <Activity className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">Total Slot Capacity</span>
            <p className="text-2xl font-bold text-indigo-300 mt-1">
              {totalSlots} <span className="text-xs font-normal text-slate-400">slots</span>
            </p>
          </div>
          <div className="p-3 rounded-xl bg-indigo-950/60 border border-indigo-800/40 text-indigo-400">
            <Cpu className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Workers Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {workers.map((w) => {
          const hbSecondsAgo = Math.round(
            (new Date().getTime() - new Date(w.last_heartbeat).getTime()) / 1000
          );
          const isStale = hbSecondsAgo > 15 || w.is_stale;

          return (
            <div
              key={w.id}
              className={`bg-slate-900/70 border rounded-xl p-5 transition-all flex flex-col justify-between ${
                w.status === 'ONLINE'
                  ? 'border-slate-800 hover:border-slate-700'
                  : 'border-slate-800/60 opacity-75'
              }`}
            >
              <div>
                {/* Worker Top */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div
                      className={`w-8 h-8 rounded-lg flex items-center justify-center border ${
                        w.status === 'ONLINE'
                          ? 'bg-emerald-950/80 border-emerald-800 text-emerald-400'
                          : 'bg-slate-800 border-slate-700 text-slate-400'
                      }`}
                    >
                      <Cpu className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-white leading-snug">{w.worker_name}</h3>
                      <p className="text-[11px] font-mono text-slate-400 flex items-center gap-1">
                        <Server className="w-3 h-3 text-slate-500" /> {w.hostname}
                      </p>
                    </div>
                  </div>

                  <StatusBadge status={w.status} />
                </div>

                {/* Slots and Load */}
                <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80 space-y-2 mb-4">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400">Concurrency Limit:</span>
                    <span className="text-slate-200 font-mono font-semibold">{w.concurrency} slots</span>
                  </div>

                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400">Active Executions:</span>
                    <span className="text-sky-400 font-mono font-semibold">{w.active_jobs}</span>
                  </div>

                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400">Available Slots:</span>
                    <span className="text-emerald-400 font-mono font-semibold">{w.available_slots}</span>
                  </div>

                  {/* Progress bar */}
                  <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-sky-500 h-1.5 rounded-full transition-all"
                      style={{
                        width: `${w.concurrency > 0 ? (w.active_jobs / w.concurrency) * 100 : 0}%`,
                      }}
                    />
                  </div>
                </div>

                {/* Heartbeat Status */}
                <div className="flex items-center justify-between text-[11px] text-slate-400 mb-3 px-1">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3 text-slate-500" />
                    Heartbeat: {hbSecondsAgo}s ago
                  </span>
                  {isStale && w.status === 'ONLINE' && (
                    <span className="text-amber-400 font-medium flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" /> Stale
                    </span>
                  )}
                </div>
              </div>

              {/* Bottom Action */}
              <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
                <span className="text-[10px] font-mono text-slate-500">ID: {w.id.substring(0, 8)}...</span>
                <button
                  onClick={() => handleViewHeartbeats(w.id)}
                  className="flex items-center gap-1 text-xs font-semibold text-sky-400 hover:text-sky-300 px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-800 transition-colors"
                >
                  <History className="w-3.5 h-3.5" />
                  Telemetry
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Heartbeats Modal */}
      <Modal
        isOpen={isHbModalOpen}
        onClose={() => setIsHbModalOpen(false)}
        title="Worker Heartbeat Telemetry History"
        maxWidth="lg"
      >
        <div className="space-y-3">
          <p className="text-xs text-slate-400">
            Recent heartbeat pings (every 5 seconds) reporting active asyncio coroutine loads.
          </p>

          <div className="bg-slate-950 rounded-xl border border-slate-800 overflow-hidden max-h-72 overflow-y-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900 text-slate-400 uppercase font-semibold border-b border-slate-800">
                <tr>
                  <th className="px-4 py-2.5">Heartbeat Time</th>
                  <th className="px-4 py-2.5">Active Jobs</th>
                  <th className="px-4 py-2.5">Available Slots</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-300">
                {heartbeats.map((hb) => (
                  <tr key={hb.id}>
                    <td className="px-4 py-2 font-mono text-slate-400">
                      {new Date(hb.heartbeat_at).toLocaleTimeString()}
                    </td>
                    <td className="px-4 py-2 font-mono font-semibold text-sky-400">{hb.active_jobs}</td>
                    <td className="px-4 py-2 font-mono font-semibold text-emerald-400">{hb.available_slots}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Modal>
    </div>
  );
};
