import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  RotateCcw,
  Clock,
  Cpu,
  Layers,
  Terminal,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Copy,
  Check,
} from 'lucide-react';
import { JobDetail } from '../types';
import { api } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';
import { usePolling } from '../hooks/usePolling';

export const JobDetails: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<JobDetail | null>(null);
  const [copied, setCopied] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);

  const fetchJob = async () => {
    if (!jobId) return;
    try {
      const data = await api.getJob(jobId);
      setJob(data);
    } catch (e) {
      console.error('Failed to load job details', e);
    }
  };

  usePolling(fetchJob, 3000);

  const handleCopyPayload = () => {
    if (!job) return;
    navigator.clipboard.writeText(JSON.stringify(job.payload, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRetry = async () => {
    if (!jobId) return;
    setIsRetrying(true);
    try {
      const updated = await api.retryJob(jobId);
      setJob(updated);
    } catch (e) {
      console.error('Failed to retry job', e);
    } finally {
      setIsRetrying(false);
    }
  };

  if (!job) {
    return (
      <div className="p-12 text-center text-slate-400">
        Loading job telemetry...
      </div>
    );
  }

  const canRetry = job.status === 'DEAD_LETTER' || job.status === 'FAILED';

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <Link
            to="/jobs"
            className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-white tracking-tight">Job Details</h2>
              <StatusBadge status={job.status} size="md" />
            </div>
            <p className="text-xs font-mono text-slate-400 mt-0.5">ID: {job.id}</p>
          </div>
        </div>

        {canRetry && (
          <button
            onClick={handleRetry}
            disabled={isRetrying}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-600/30 transition-all disabled:opacity-50"
          >
            <RotateCcw className={`w-4 h-4 ${isRetrying ? 'animate-spin' : ''}`} />
            {isRetrying ? 'Requeueing...' : 'Requeue from Dead Letter / Failed'}
          </button>
        )}
      </div>

      {/* Overview Metadata Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
          <span className="text-xs text-slate-400 font-medium">Job Handler</span>
          <p className="text-base font-bold text-white mt-1 font-mono">{job.job_type}</p>
          <p className="text-[11px] text-slate-500 mt-0.5">Executor logic</p>
        </div>

        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
          <span className="text-xs text-slate-400 font-medium">Target Queue</span>
          <p className="text-base font-bold text-sky-400 mt-1 font-mono">{job.queue_name || 'default'}</p>
          <p className="text-[11px] text-slate-500 mt-0.5">Priority: {job.priority}</p>
        </div>

        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
          <span className="text-xs text-slate-400 font-medium">Execution Attempts</span>
          <p className="text-base font-bold text-amber-400 mt-1 font-mono">
            {job.attempts} / {job.max_attempts}
          </p>
          <p className="text-[11px] text-slate-500 mt-0.5">Maximum attempts before DLQ</p>
        </div>

        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
          <span className="text-xs text-slate-400 font-medium">Available At</span>
          <p className="text-base font-bold text-slate-200 mt-1 font-mono">
            {new Date(job.available_at).toLocaleTimeString()}
          </p>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Created: {new Date(job.created_at).toLocaleTimeString()}
          </p>
        </div>
      </div>

      {/* Dead Letter Alert Card if applicable */}
      {job.dead_letter && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/80 text-rose-200">
          <div className="flex items-center gap-2 font-bold text-sm text-rose-300 mb-1">
            <AlertTriangle className="w-4 h-4 text-rose-400" />
            Dead Letter Diagnostic Information
          </div>
          <p className="text-xs text-rose-300 mb-2">Reason: {job.dead_letter.reason}</p>
          {job.dead_letter.final_error && (
            <div className="bg-slate-950/80 p-3 rounded-lg border border-rose-900/60 font-mono text-xs text-rose-400 overflow-x-auto">
              {job.dead_letter.final_error}
            </div>
          )}
        </div>
      )}

      {/* Payload & Execution History Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Payload */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden flex flex-col">
          <div className="px-5 py-3 border-b border-slate-800 bg-slate-900/80 flex items-center justify-between">
            <span className="text-xs font-semibold text-white uppercase tracking-wider">
              Input Payload (JSON)
            </span>
            <button
              onClick={handleCopyPayload}
              className="flex items-center gap-1 text-xs text-slate-400 hover:text-white px-2 py-1 rounded bg-slate-800 transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
          <div className="p-4 flex-1 bg-slate-950 overflow-x-auto">
            <pre className="text-xs font-mono text-emerald-400 leading-relaxed">
              {JSON.stringify(job.payload, null, 2)}
            </pre>
          </div>
        </div>

        {/* Execution History */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden flex flex-col">
          <div className="px-5 py-3 border-b border-slate-800 bg-slate-900/80">
            <span className="text-xs font-semibold text-white uppercase tracking-wider">
              Attempt Execution History ({job.executions.length})
            </span>
          </div>
          <div className="p-4 space-y-3 flex-1 overflow-y-auto max-h-80">
            {job.executions.length === 0 ? (
              <p className="text-xs text-slate-500 italic">No execution attempts recorded yet.</p>
            ) : (
              job.executions.map((ex) => (
                <div
                  key={ex.id}
                  className="bg-slate-950/60 p-3 rounded-lg border border-slate-800 text-xs space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-white">
                      Attempt #{ex.attempt_number}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        ex.status === 'COMPLETED'
                          ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                          : ex.status === 'RUNNING'
                          ? 'bg-sky-950 text-sky-300 border border-sky-800'
                          : 'bg-red-950 text-red-300 border border-red-800'
                      }`}
                    >
                      {ex.status}
                    </span>
                  </div>

                  <div className="text-slate-400 flex items-center justify-between">
                    <span>Duration: {ex.duration_ms !== null ? `${ex.duration_ms} ms` : 'In progress...'}</span>
                    <span className="font-mono text-slate-500">Worker: {ex.worker_id?.substring(0, 8) || 'N/A'}</span>
                  </div>

                  {ex.error_message && (
                    <p className="text-rose-400 font-mono text-[11px] bg-rose-950/30 p-2 rounded border border-rose-900/40">
                      {ex.error_message}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Execution Logs Terminal */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-800 bg-slate-900/80 flex items-center gap-2 text-xs font-semibold text-white uppercase tracking-wider">
          <Terminal className="w-4 h-4 text-sky-400" />
          Job Execution Logs ({job.logs.length})
        </div>
        <div className="p-4 bg-slate-950 font-mono text-xs max-h-72 overflow-y-auto space-y-1.5 divide-y divide-slate-900">
          {job.logs.length === 0 ? (
            <p className="text-slate-500 italic py-2">No logs streamed for this job.</p>
          ) : (
            job.logs.map((lg) => {
              const levelColor = {
                INFO: 'text-sky-400',
                WARN: 'text-amber-400',
                ERROR: 'text-rose-400',
                DEBUG: 'text-purple-400',
              }[lg.level] || 'text-slate-400';

              return (
                <div key={lg.id} className="pt-1.5 flex items-start gap-3">
                  <span className="text-slate-500 text-[11px] flex-shrink-0">
                    {new Date(lg.timestamp).toLocaleTimeString()}
                  </span>
                  <span className={`font-bold text-[10px] uppercase px-1.5 py-0.2 rounded bg-slate-900 ${levelColor} border border-slate-800`}>
                    {lg.level}
                  </span>
                  <span className="text-slate-300 flex-1 break-words">{lg.message}</span>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
