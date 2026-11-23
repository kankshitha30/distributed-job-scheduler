import React, { useState } from 'react';
import { Modal } from './Modal';
import { Queue } from '../types';
import { api } from '../services/api';
import { Plus, Sparkles, AlertCircle } from 'lucide-react';

interface JobCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  queues: Queue[];
  onJobCreated: () => void;
  defaultQueueId?: string;
}

export const JobCreateModal: React.FC<JobCreateModalProps> = ({
  isOpen,
  onClose,
  queues,
  onJobCreated,
  defaultQueueId,
}) => {
  const [selectedQueue, setSelectedQueue] = useState<string>(
    defaultQueueId || (queues.length > 0 ? queues[0].id : '')
  );
  const [jobType, setJobType] = useState<string>('echo');
  const [priority, setPriority] = useState<number>(0);
  const [schedulingType, setSchedulingType] = useState<'immediate' | 'delayed' | 'scheduled' | 'cron' | 'batch'>('immediate');
  const [delaySeconds, setDelaySeconds] = useState<number>(10);
  const [scheduledAt, setScheduledAt] = useState<string>('');
  const [cronExpression, setCronExpression] = useState<string>('*/5 * * * *');
  const [batchCount, setBatchCount] = useState<number>(5);
  const [payloadText, setPayloadText] = useState<string>(
    JSON.stringify({ message: 'Hello from Dashboard!' }, null, 2)
  );
  const [idempotencyKey, setIdempotencyKey] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const applyTemplate = (type: string) => {
    setJobType(type);
    setError(null);
    switch (type) {
      case 'echo':
        setPayloadText(JSON.stringify({ message: 'Hello from Distributed Scheduler!', timestamp: new Date().toISOString() }, null, 2));
        break;
      case 'sleep':
        setPayloadText(JSON.stringify({ seconds: 3, task_name: 'simulated_data_sync' }, null, 2));
        break;
      case 'calculation':
        setPayloadText(JSON.stringify({ operation: 'fibonacci', n: 32 }, null, 2));
        break;
      case 'email_simulation':
        setPayloadText(JSON.stringify({ to: 'demo@company.com', subject: 'Your Monthly Report', template: 'monthly_digest' }, null, 2));
        break;
      case 'intentional_failure':
        setPayloadText(JSON.stringify({ error: 'Simulated payment gateway timeout', fail_times: 4 }, null, 2));
        break;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedQueue) {
      setError('Please select a queue');
      return;
    }

    let parsedPayload = {};
    try {
      parsedPayload = JSON.parse(payloadText);
    } catch (pe) {
      setError('Payload must be valid JSON');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      if (schedulingType === 'batch') {
        const batchItems = Array.from({ length: batchCount }).map((_, idx) => ({
          job_type: jobType,
          payload: { ...parsedPayload, batch_index: idx + 1 },
          priority,
        }));
        await api.createBatchJobs(selectedQueue, batchItems);
      } else {
        const payload: any = {
          job_type: jobType,
          payload: parsedPayload,
          priority,
        };
        if (schedulingType === 'delayed') {
          payload.delay_seconds = delaySeconds;
        } else if (schedulingType === 'scheduled' && scheduledAt) {
          payload.scheduled_at = new Date(scheduledAt).toISOString();
        } else if (schedulingType === 'cron') {
          payload.cron_expression = cronExpression;
        }

        await api.createJob(selectedQueue, payload, idempotencyKey.trim() || undefined);
      }

      onJobCreated();
      onClose();
    } catch (err: any) {
      const msg = err.response?.data?.error?.message || err.message || 'Failed to create job';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create New Background Job" maxWidth="2xl">
      <form onSubmit={handleSubmit} className="space-y-5">
        {error && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-red-950/60 border border-red-800 text-red-300 text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Queue Selection */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
            Target Queue
          </label>
          <select
            value={selectedQueue}
            onChange={(e) => setSelectedQueue(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3.5 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-sky-500"
            required
          >
            {queues.map((q) => (
              <option key={q.id} value={q.id}>
                {q.name} (Priority: {q.priority}, Concurrency: {q.concurrency_limit}{q.paused ? ' - PAUSED' : ''})
              </option>
            ))}
          </select>
        </div>

        {/* Templates quick selector */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Job Handler Template
            </label>
            <span className="text-[11px] text-sky-400 flex items-center gap-1">
              <Sparkles className="w-3 h-3" /> Quick Presets
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {[
              { id: 'echo', label: 'Echo' },
              { id: 'sleep', label: 'Async Sleep' },
              { id: 'calculation', label: 'Calculation' },
              { id: 'email_simulation', label: 'Email Simulation' },
              { id: 'intentional_failure', label: 'Failure (DLQ Demo)' },
            ].map((t) => (
              <button
                type="button"
                key={t.id}
                onClick={() => applyTemplate(t.id)}
                className={`px-3 py-2 rounded-lg text-xs font-medium border text-left transition-colors ${
                  jobType === t.id
                    ? 'bg-sky-950 border-sky-600 text-sky-200'
                    : 'bg-slate-800/60 border-slate-700/80 text-slate-300 hover:bg-slate-800'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Schedule Mode */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
            Execution Timing
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
            {[
              { id: 'immediate', label: 'Immediate' },
              { id: 'delayed', label: 'Delayed' },
              { id: 'scheduled', label: 'Scheduled' },
              { id: 'cron', label: 'Recurring' },
              { id: 'batch', label: 'Batch' },
            ].map((mode) => (
              <button
                type="button"
                key={mode.id}
                onClick={() => setSchedulingType(mode.id as any)}
                className={`px-3 py-2 rounded-lg text-xs font-medium border text-center transition-colors ${
                  schedulingType === mode.id
                    ? 'bg-sky-600 border-sky-500 text-white font-semibold shadow-sm'
                    : 'bg-slate-800/40 border-slate-700/60 text-slate-400 hover:text-slate-200'
                }`}
              >
                {mode.label}
              </button>
            ))}
          </div>
        </div>

        {/* Timing options detail */}
        {schedulingType === 'delayed' && (
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Delay (seconds)</label>
            <input
              type="number"
              min="1"
              max="86400"
              value={delaySeconds}
              onChange={(e) => setDelaySeconds(parseInt(e.target.value) || 1)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
          </div>
        )}

        {schedulingType === 'scheduled' && (
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Scheduled At (UTC / Local)</label>
            <input
              type="datetime-local"
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-sky-500"
              required
            />
          </div>
        )}

        {schedulingType === 'cron' && (
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Cron Expression (e.g. `*/5 * * * *`)</label>
            <input
              type="text"
              value={cronExpression}
              onChange={(e) => setCronExpression(e.target.value)}
              placeholder="*/5 * * * *"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3.5 py-2 text-sm font-mono text-white focus:outline-none focus:ring-2 focus:ring-sky-500"
              required
            />
          </div>
        )}

        {schedulingType === 'batch' && (
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Batch Job Count</label>
            <input
              type="number"
              min="2"
              max="50"
              value={batchCount}
              onChange={(e) => setBatchCount(parseInt(e.target.value) || 2)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
          </div>
        )}

        {/* Priority & Idempotency Key */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Priority (0 = Normal, 10+ = High)</label>
            <input
              type="number"
              min="0"
              max="100"
              value={priority}
              onChange={(e) => setPriority(parseInt(e.target.value) || 0)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Idempotency Key (Optional)</label>
            <input
              type="text"
              value={idempotencyKey}
              onChange={(e) => setIdempotencyKey(e.target.value)}
              placeholder="e.g. order-tx-9941"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3.5 py-2 text-sm font-mono text-white focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
          </div>
        </div>

        {/* Payload JSON */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
            Payload (JSON)
          </label>
          <textarea
            rows={5}
            value={payloadText}
            onChange={(e) => setPayloadText(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-xs font-mono text-emerald-400 focus:outline-none focus:ring-2 focus:ring-sky-500"
            required
          />
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-medium bg-sky-600 hover:bg-sky-500 text-white shadow-lg shadow-sky-600/30 transition-all disabled:opacity-50"
          >
            <Plus className="w-4 h-4" />
            {loading ? 'Submitting...' : schedulingType === 'batch' ? `Create ${batchCount} Batch Jobs` : 'Enqueue Job'}
          </button>
        </div>
      </form>
    </Modal>
  );
};
