import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  Search,
  Filter,
  Plus,
  RotateCw,
  ChevronLeft,
  ChevronRight,
  Eye,
} from 'lucide-react';
import { Job, Queue } from '../types';
import { api } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';
import { JobCreateModal } from '../components/JobCreateModal';
import { usePolling } from '../hooks/usePolling';

export const JobExplorer: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [queues, setQueues] = useState<Queue[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(15);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>(searchParams.get('status') || '');
  const [queueFilter, setQueueFilter] = useState<string>(searchParams.get('queue_id') || '');
  const [jobTypeFilter, setJobTypeFilter] = useState<string>('');
  const [searchId, setSearchId] = useState<string>('');

  const [isJobModalOpen, setIsJobModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const fetchQueues = async () => {
    try {
      const qList = await api.getQueues();
      setQueues(qList);
    } catch (e) {
      console.error('Failed to load queues', e);
    }
  };

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const res = await api.getJobs({
        queue_id: queueFilter || undefined,
        status: statusFilter || undefined,
        job_type: jobTypeFilter || undefined,
        page,
        page_size: pageSize,
      });

      let filteredItems = res.items;
      if (searchId.trim()) {
        filteredItems = filteredItems.filter((j) =>
          j.id.toLowerCase().includes(searchId.trim().toLowerCase())
        );
      }
      setJobs(filteredItems);
      setTotal(res.total);
    } catch (e) {
      console.error('Failed to fetch jobs', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueues();
  }, []);

  usePolling(fetchJobs, 4000);

  const handleFilterChange = (key: string, value: string) => {
    if (key === 'status') setStatusFilter(value);
    if (key === 'queue') setQueueFilter(value);
    if (key === 'type') setJobTypeFilter(value);
    setPage(1);

    // Update query params
    const newParams = new URLSearchParams(searchParams);
    if (value) {
      newParams.set(key, value);
    } else {
      newParams.delete(key);
    }
    setSearchParams(newParams);
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Job Explorer</h2>
          <p className="text-sm text-slate-400">
            Search, filter, and inspect individual job lifecycles and execution attempts.
          </p>
        </div>
        <button
          onClick={() => setIsJobModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-sky-600 hover:bg-sky-500 text-white shadow-lg shadow-sky-600/30 transition-all"
        >
          <Plus className="w-4 h-4" />
          Enqueue Job
        </button>
      </div>

      {/* Filter Bar */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
        {/* Search ID */}
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search by Job ID..."
            value={searchId}
            onChange={(e) => setSearchId(e.target.value)}
            className="w-full bg-slate-800/80 border border-slate-700 rounded-lg pl-9 pr-3.5 py-2 text-xs text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
        </div>

        {/* Status Filter */}
        <div>
          <select
            value={statusFilter}
            onChange={(e) => handleFilterChange('status', e.target.value)}
            className="w-full bg-slate-800/80 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:ring-2 focus:ring-sky-500"
          >
            <option value="">All Statuses</option>
            <option value="QUEUED">QUEUED</option>
            <option value="SCHEDULED">SCHEDULED</option>
            <option value="CLAIMED">CLAIMED</option>
            <option value="RUNNING">RUNNING</option>
            <option value="COMPLETED">COMPLETED</option>
            <option value="FAILED">FAILED</option>
            <option value="RETRYING">RETRYING</option>
            <option value="DEAD_LETTER">DEAD LETTER</option>
          </select>
        </div>

        {/* Queue Filter */}
        <div>
          <select
            value={queueFilter}
            onChange={(e) => handleFilterChange('queue', e.target.value)}
            className="w-full bg-slate-800/80 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:ring-2 focus:ring-sky-500"
          >
            <option value="">All Queues</option>
            {queues.map((q) => (
              <option key={q.id} value={q.id}>
                Queue: {q.name}
              </option>
            ))}
          </select>
        </div>

        {/* Job Type Filter */}
        <div>
          <select
            value={jobTypeFilter}
            onChange={(e) => handleFilterChange('type', e.target.value)}
            className="w-full bg-slate-800/80 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:ring-2 focus:ring-sky-500"
          >
            <option value="">All Job Types</option>
            <option value="echo">echo</option>
            <option value="sleep">sleep</option>
            <option value="calculation">calculation</option>
            <option value="email_simulation">email_simulation</option>
            <option value="intentional_failure">intentional_failure</option>
          </select>
        </div>
      </div>

      {/* Jobs Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-950/60 text-slate-400 text-xs uppercase font-semibold border-b border-slate-800">
              <tr>
                <th className="px-6 py-3.5">Job ID</th>
                <th className="px-6 py-3.5">Type</th>
                <th className="px-6 py-3.5">Queue</th>
                <th className="px-6 py-3.5">Status</th>
                <th className="px-6 py-3.5">Priority</th>
                <th className="px-6 py-3.5">Attempts</th>
                <th className="px-6 py-3.5">Available At</th>
                <th className="px-6 py-3.5">Created</th>
                <th className="px-6 py-3.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {jobs.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-6 py-12 text-center text-slate-500">
                    {loading ? 'Fetching jobs...' : 'No matching jobs found.'}
                  </td>
                </tr>
              ) : (
                jobs.map((j) => (
                  <tr key={j.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-6 py-4 font-mono text-xs text-sky-400">
                      <Link to={`/jobs/${j.id}`} className="hover:underline">
                        {j.id.substring(0, 8)}...
                      </Link>
                    </td>
                    <td className="px-6 py-4 font-medium text-white">{j.job_type}</td>
                    <td className="px-6 py-4 text-xs font-mono text-slate-300">{j.queue_name || 'default'}</td>
                    <td className="px-6 py-4">
                      <StatusBadge status={j.status} />
                    </td>
                    <td className="px-6 py-4 font-mono text-xs">{j.priority}</td>
                    <td className="px-6 py-4 font-mono text-xs">
                      {j.attempts} / {j.max_attempts}
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-400">
                      {new Date(j.available_at).toLocaleTimeString()}
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-500">
                      {new Date(j.created_at).toLocaleTimeString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        to={`/jobs/${j.id}`}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        Details
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="px-6 py-3.5 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <div>
            Showing <strong className="text-white">{jobs.length}</strong> of <strong className="text-white">{total}</strong> total jobs
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="p-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:text-white disabled:opacity-40 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-mono px-2">
              {page} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="p-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:text-white disabled:opacity-40 transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Enqueue Modal */}
      <JobCreateModal
        isOpen={isJobModalOpen}
        onClose={() => setIsJobModalOpen(false)}
        queues={queues}
        onJobCreated={fetchJobs}
      />
    </div>
  );
};
