import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Layers,
  ArrowLeft,
  Play,
  Pause,
  Plus,
  RotateCcw,
  Shield,
  Clock,
  CheckCircle2,
  XCircle,
  AlertOctagon,
  Eye,
} from 'lucide-react';
import { Queue, Job } from '../types';
import { api } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';
import { JobCreateModal } from '../components/JobCreateModal';
import { usePolling } from '../hooks/usePolling';

export const QueueDetails: React.FC = () => {
  const { queueId } = useParams<{ queueId: string }>();
  const [queue, setQueue] = useState<Queue | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [deadLetters, setDeadLetters] = useState<Job[]>([]);
  const [activeTab, setActiveTab] = useState<'jobs' | 'dlq'>('jobs');
  const [isJobModalOpen, setIsJobModalOpen] = useState(false);
  const [retryingId, setRetryingId] = useState<string | null>(null);

  const fetchData = async () => {
    if (!queueId) return;
    try {
      const qData = await api.getQueue(queueId);
      const [statsData, jobsData, dlqData] = await Promise.all([
        api.getQueueStats(queueId),
        api.getJobs({ queue_id: queueId, page: 1, page_size: 20 }),
        api.getQueueDeadLetters(queueId, 1, 50),
      ]);
      setQueue({ ...qData, stats: statsData });
      setJobs(jobsData.items);
      setDeadLetters(dlqData.items);
    } catch (e) {
      console.error('Failed to load queue details', e);
    }
  };

  usePolling(fetchData, 4000);

  const handleTogglePause = async () => {
    if (!queue) return;
    try {
      if (queue.paused) {
        await api.resumeQueue(queue.id);
      } else {
        await api.pauseQueue(queue.id);
      }
      fetchData();
    } catch (e) {
      console.error('Failed to toggle pause', e);
    }
  };

  const handleRetryDlq = async (jobId: string) => {
    setRetryingId(jobId);
    try {
      await api.retryJob(jobId);
      await fetchData();
    } catch (e) {
      console.error('Failed to retry dead letter job', e);
    } finally {
      setRetryingId(null);
    }
  };

  if (!queue) {
    return (
      <div className="p-8 text-center text-slate-400">
        Loading queue configuration...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back button & Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <Link
            to="/queues"
            className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-2xl font-bold text-white tracking-tight">{queue.name}</h2>
              {queue.paused ? (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-950 text-amber-300 border border-amber-800">
                  PAUSED
                </span>
              ) : (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">
                  ACTIVE
                </span>
              )}
            </div>
            <p className="text-xs font-mono text-slate-400 mt-0.5">Queue ID: {queue.id}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleTogglePause}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold border transition-colors ${
              queue.paused
                ? 'bg-emerald-950 border-emerald-800 text-emerald-300 hover:bg-emerald-900'
                : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
            }`}
          >
            {queue.paused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
            {queue.paused ? 'Resume Queue' : 'Pause Queue'}
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

      {/* Queue Config & Metadata Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
          <span className="text-xs text-slate-400 font-medium">Concurrency Limit</span>
          <p className="text-2xl font-bold text-white mt-1 font-mono">{queue.concurrency_limit}</p>
          <p className="text-[11px] text-slate-500 mt-1">Max simultaneous active workers</p>
        </div>

        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
          <span className="text-xs text-slate-400 font-medium">Queue Priority</span>
          <p className="text-2xl font-bold text-white mt-1 font-mono">{queue.priority}</p>
          <p className="text-[11px] text-slate-500 mt-1">Higher values claim first</p>
        </div>

        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
          <span className="text-xs text-slate-400 font-medium">Retry Strategy</span>
          <p className="text-lg font-bold text-indigo-300 mt-1 capitalize">
            {queue.retry_policy?.strategy || 'None'}
          </p>
          <p className="text-[11px] text-slate-500 mt-1">
            {queue.retry_policy
              ? `${queue.retry_policy.max_attempts} attempts | ${queue.retry_policy.initial_delay_seconds}s delay`
              : 'No policy attached'}
          </p>
        </div>

        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
          <span className="text-xs text-slate-400 font-medium">Success Rate</span>
          <p className="text-2xl font-bold text-emerald-400 mt-1 font-mono">
            {queue.stats?.success_rate || 100}%
          </p>
          <p className="text-[11px] text-slate-500 mt-1">
            Avg Duration: {queue.stats?.average_execution_time_ms || 0}ms
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-800">
        <div className="flex gap-6">
          <button
            onClick={() => setActiveTab('jobs')}
            className={`pb-3 text-sm font-semibold border-b-2 transition-all ${
              activeTab === 'jobs'
                ? 'border-sky-500 text-sky-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Recent Jobs ({jobs.length})
          </button>
          <button
            onClick={() => setActiveTab('dlq')}
            className={`pb-3 text-sm font-semibold border-b-2 flex items-center gap-2 transition-all ${
              activeTab === 'dlq'
                ? 'border-rose-500 text-rose-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <AlertOctagon className="w-4 h-4" />
            Dead Letter Queue ({deadLetters.length})
          </button>
        </div>
      </div>

      {/* Tab 1: Recent Jobs */}
      {activeTab === 'jobs' && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-950/60 text-slate-400 text-xs uppercase font-semibold border-b border-slate-800">
                <tr>
                  <th className="px-6 py-3.5">Job ID</th>
                  <th className="px-6 py-3.5">Type</th>
                  <th className="px-6 py-3.5">Status</th>
                  <th className="px-6 py-3.5">Priority</th>
                  <th className="px-6 py-3.5">Attempts</th>
                  <th className="px-6 py-3.5">Available At</th>
                  <th className="px-6 py-3.5 text-right">View</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {jobs.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-slate-500">
                      No jobs in this queue yet.
                    </td>
                  </tr>
                ) : (
                  jobs.map((j) => (
                    <tr key={j.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="px-6 py-3.5 font-mono text-xs text-sky-400">
                        <Link to={`/jobs/${j.id}`} className="hover:underline">
                          {j.id.substring(0, 13)}...
                        </Link>
                      </td>
                      <td className="px-6 py-3.5 font-medium text-white">{j.job_type}</td>
                      <td className="px-6 py-3.5">
                        <StatusBadge status={j.status} />
                      </td>
                      <td className="px-6 py-3.5 font-mono text-xs">{j.priority}</td>
                      <td className="px-6 py-3.5 font-mono text-xs">
                        {j.attempts} / {j.max_attempts}
                      </td>
                      <td className="px-6 py-3.5 text-xs text-slate-400">
                        {new Date(j.available_at).toLocaleTimeString()}
                      </td>
                      <td className="px-6 py-3.5 text-right">
                        <Link
                          to={`/jobs/${j.id}`}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 inline-flex items-center"
                        >
                          <Eye className="w-4 h-4" />
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 2: Dead Letter Queue */}
      {activeTab === 'dlq' && (
        <div className="space-y-4">
          <div className="bg-rose-950/20 border border-rose-900/40 rounded-xl p-4 text-xs text-rose-200">
            <p className="font-semibold text-rose-300 mb-1">About Dead Letter Queue (DLQ)</p>
            Jobs that have exhausted all maximum retry attempts are isolated here to protect queue throughput. You can inspect the final failure reason and manually requeue any job.
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-950/60 text-slate-400 text-xs uppercase font-semibold border-b border-slate-800">
                  <tr>
                    <th className="px-6 py-3.5">Job ID</th>
                    <th className="px-6 py-3.5">Type</th>
                    <th className="px-6 py-3.5">Attempts</th>
                    <th className="px-6 py-3.5">Failed At</th>
                    <th className="px-6 py-3.5 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {deadLetters.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-8 text-center text-slate-500">
                        Zero jobs in Dead Letter Queue. Everything running cleanly!
                      </td>
                    </tr>
                  ) : (
                    deadLetters.map((dl) => (
                      <tr key={dl.id} className="hover:bg-slate-800/40 transition-colors">
                        <td className="px-6 py-3.5 font-mono text-xs text-rose-400">
                          <Link to={`/jobs/${dl.id}`} className="hover:underline">
                            {dl.id.substring(0, 13)}...
                          </Link>
                        </td>
                        <td className="px-6 py-3.5 font-medium text-white">{dl.job_type}</td>
                        <td className="px-6 py-3.5 font-mono text-xs">
                          {dl.attempts} / {dl.max_attempts}
                        </td>
                        <td className="px-6 py-3.5 text-xs text-slate-400">
                          {new Date(dl.updated_at).toLocaleString()}
                        </td>
                        <td className="px-6 py-3.5 text-right">
                          <button
                            onClick={() => handleRetryDlq(dl.id)}
                            disabled={retryingId === dl.id}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-950 hover:bg-rose-900 text-rose-200 border border-rose-800 ml-auto transition-colors disabled:opacity-50"
                          >
                            <RotateCcw className={`w-3.5 h-3.5 ${retryingId === dl.id ? 'animate-spin' : ''}`} />
                            {retryingId === dl.id ? 'Requeueing...' : 'Requeue Job'}
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Enqueue Modal */}
      <JobCreateModal
        isOpen={isJobModalOpen}
        onClose={() => setIsJobModalOpen(false)}
        queues={[queue]}
        onJobCreated={fetchData}
        defaultQueueId={queue.id}
      />
    </div>
  );
};
