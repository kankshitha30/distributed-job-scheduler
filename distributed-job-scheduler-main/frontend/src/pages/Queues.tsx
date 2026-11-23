import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Layers,
  Plus,
  Play,
  Pause,
  ArrowRight,
  Shield,
  Clock,
  Activity,
  Trash2,
} from 'lucide-react';
import { Queue, Project } from '../types';
import { api } from '../services/api';
import { QueueCreateModal } from '../components/QueueCreateModal';
import { JobCreateModal } from '../components/JobCreateModal';

interface QueuesProps {
  queues: Queue[];
  onRefresh: () => void;
}

export const Queues: React.FC<QueuesProps> = ({ queues, onRefresh }) => {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isJobModalOpen, setIsJobModalOpen] = useState(false);
  const [selectedQueueForJob, setSelectedQueueForJob] = useState<string>('');
  const [projects, setProjects] = useState<Project[]>([]);

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const p = await api.getProjects();
        setProjects(p);
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

  const handleDeleteQueue = async (queueId: string) => {
    if (!window.confirm('Are you sure you want to delete this queue? All jobs inside will be deleted.')) {
      return;
    }
    try {
      await api.deleteQueue(queueId);
      onRefresh();
    } catch (e) {
      console.error('Failed to delete queue', e);
    }
  };

  const openJobModal = (queueId: string) => {
    setSelectedQueueForJob(queueId);
    setIsJobModalOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Queue Management</h2>
          <p className="text-sm text-slate-400">
            Configure concurrency limits, retry strategies, and real-time execution states.
          </p>
        </div>
        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-sky-600 hover:bg-sky-500 text-white shadow-lg shadow-sky-600/30 transition-all"
        >
          <Plus className="w-4 h-4" />
          New Queue
        </button>
      </div>

      {/* Queues Grid / Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {queues.map((q) => (
          <div
            key={q.id}
            className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-all flex flex-col justify-between"
          >
            <div>
              {/* Card Header */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-sky-950 border border-sky-800/60 flex items-center justify-center text-sky-400">
                    <Layers className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-white leading-snug">{q.name}</h3>
                    <span className="text-[11px] font-mono text-slate-400">
                      Priority: {q.priority} | Limit: {q.concurrency_limit}
                    </span>
                  </div>
                </div>

                <div>
                  {q.paused ? (
                    <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-950 text-amber-300 border border-amber-800">
                      PAUSED
                    </span>
                  ) : (
                    <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">
                      ACTIVE
                    </span>
                  )}
                </div>
              </div>

              {/* Policy & Info */}
              <div className="space-y-1.5 text-xs text-slate-400 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80 mb-4">
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1">
                    <Shield className="w-3.5 h-3.5 text-indigo-400" /> Retry Strategy:
                  </span>
                  <span className="text-slate-200 font-medium">
                    {q.retry_policy ? `${q.retry_policy.strategy} (${q.retry_policy.max_attempts} max)` : 'None'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5 text-slate-400" /> Avg Latency:
                  </span>
                  <span className="text-slate-200 font-mono">
                    {q.stats?.average_execution_time_ms || 0} ms
                  </span>
                </div>
              </div>

              {/* Stat Counters */}
              <div className="grid grid-cols-4 gap-2 text-center text-xs mb-4">
                <div className="bg-slate-800/40 p-2 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase">Queued</span>
                  <p className="text-sm font-bold text-slate-200 mt-0.5">{q.stats?.queued_jobs || 0}</p>
                </div>
                <div className="bg-slate-800/40 p-2 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase">Running</span>
                  <p className="text-sm font-bold text-sky-400 mt-0.5">{q.stats?.running_jobs || 0}</p>
                </div>
                <div className="bg-slate-800/40 p-2 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase">Done</span>
                  <p className="text-sm font-bold text-emerald-400 mt-0.5">{q.stats?.completed_jobs || 0}</p>
                </div>
                <div className="bg-slate-800/40 p-2 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase">DLQ</span>
                  <p className="text-sm font-bold text-rose-400 mt-0.5">{q.stats?.dead_letter_jobs || 0}</p>
                </div>
              </div>
            </div>

            {/* Actions Bar */}
            <div className="flex items-center justify-between pt-3 border-t border-slate-800 gap-2">
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => handleTogglePause(q)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold border flex items-center gap-1 transition-colors ${
                    q.paused
                      ? 'bg-emerald-950 border-emerald-800 text-emerald-300 hover:bg-emerald-900'
                      : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  {q.paused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
                  {q.paused ? 'Resume' : 'Pause'}
                </button>

                <button
                  onClick={() => openJobModal(q.id)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
                >
                  + Job
                </button>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleDeleteQueue(q.id)}
                  className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-950/40 transition-colors"
                  title="Delete Queue"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
                <Link
                  to={`/queues/${q.id}`}
                  className="flex items-center gap-1 text-xs font-semibold text-sky-400 hover:text-sky-300 px-2.5 py-1.5 rounded-lg hover:bg-slate-800 transition-colors"
                >
                  Details <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Modals */}
      <QueueCreateModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        projects={projects}
        onQueueCreated={onRefresh}
      />
      <JobCreateModal
        isOpen={isJobModalOpen}
        onClose={() => setIsJobModalOpen(false)}
        queues={queues}
        onJobCreated={onRefresh}
        defaultQueueId={selectedQueueForJob}
      />
    </div>
  );
};
