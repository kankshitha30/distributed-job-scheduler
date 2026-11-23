import React, { useState, useEffect } from 'react';
import { Modal } from './Modal';
import { Project, RetryPolicy } from '../types';
import { api } from '../services/api';
import { Layers, AlertCircle } from 'lucide-react';

interface QueueCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  projects: Project[];
  onQueueCreated: () => void;
}

export const QueueCreateModal: React.FC<QueueCreateModalProps> = ({
  isOpen,
  onClose,
  projects,
  onQueueCreated,
}) => {
  const [projectId, setProjectId] = useState<string>(projects[0]?.id || '');
  const [name, setName] = useState<string>('');
  const [priority, setPriority] = useState<number>(0);
  const [concurrencyLimit, setConcurrencyLimit] = useState<number>(5);
  const [retryPolicyId, setRetryPolicyId] = useState<string>('');
  const [retryPolicies, setRetryPolicies] = useState<RetryPolicy[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (projects.length > 0 && !projectId) {
      setProjectId(projects[0].id);
    }
  }, [projects]);

  useEffect(() => {
    const fetchPolicies = async () => {
      try {
        const policies = await api.getRetryPolicies();
        setRetryPolicies(policies);
        if (policies.length > 0 && !retryPolicyId) {
          setRetryPolicyId(policies[0].id);
        }
      } catch (e) {
        console.error('Failed to load retry policies', e);
      }
    };
    if (isOpen) {
      fetchPolicies();
    }
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectId) {
      setError('Please select a project');
      return;
    }
    if (!name.trim()) {
      setError('Queue name is required');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await api.createQueue(projectId, {
        name: name.trim().toLowerCase(),
        priority,
        concurrency_limit: concurrencyLimit,
        retry_policy_id: retryPolicyId || undefined,
      });
      onQueueCreated();
      onClose();
    } catch (err: any) {
      const msg = err.response?.data?.error?.message || err.message || 'Failed to create queue';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Configure New Job Queue" maxWidth="lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-red-950/60 border border-red-800 text-red-300 text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Project Selection */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
            Project
          </label>
          <select
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3.5 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-sky-500"
            required
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        {/* Queue Name */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
            Queue Identifier / Name
          </label>
          <input
            type="text"
            placeholder="e.g. notifications, indexing, billing"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-sky-500"
            required
          />
        </div>

        {/* Priority & Concurrency Limit */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Queue Priority (0 - 100)</label>
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
            <label className="block text-xs font-medium text-slate-400 mb-1">Concurrency Limit</label>
            <input
              type="number"
              min="1"
              max="100"
              value={concurrencyLimit}
              onChange={(e) => setConcurrencyLimit(parseInt(e.target.value) || 1)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
          </div>
        </div>

        {/* Retry Policy */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
            Retry Policy
          </label>
          <select
            value={retryPolicyId}
            onChange={(e) => setRetryPolicyId(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3.5 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-sky-500"
          >
            <option value="">None (Fail immediately)</option>
            {retryPolicies.map((rp) => (
              <option key={rp.id} value={rp.id}>
                {rp.name} ({rp.strategy}, max {rp.max_attempts} attempts, init {rp.initial_delay_seconds}s)
              </option>
            ))}
          </select>
        </div>

        {/* Actions */}
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
            <Layers className="w-4 h-4" />
            {loading ? 'Creating...' : 'Create Queue'}
          </button>
        </div>
      </form>
    </Modal>
  );
};
