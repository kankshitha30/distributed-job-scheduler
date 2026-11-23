export type JobStatus =
  | 'QUEUED'
  | 'SCHEDULED'
  | 'CLAIMED'
  | 'RUNNING'
  | 'COMPLETED'
  | 'FAILED'
  | 'RETRYING'
  | 'DEAD_LETTER';

export type WorkerStatus = 'ONLINE' | 'OFFLINE' | 'STOPPING';

export interface User {
  id: string;
  email: string;
  name: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  email: string;
  name: string;
  organization_id?: string;
}

export interface RetryPolicy {
  id: string;
  name: string;
  strategy: 'fixed' | 'linear' | 'exponential';
  max_attempts: number;
  initial_delay_seconds: number;
  backoff_multiplier: number;
}

export interface QueueStats {
  total_jobs: number;
  queued_jobs: number;
  running_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  retrying_jobs: number;
  dead_letter_jobs: number;
  average_execution_time_ms: number;
  success_rate: number;
}

export interface Queue {
  id: string;
  project_id: string;
  name: string;
  priority: number;
  concurrency_limit: number;
  paused: boolean;
  retry_policy_id?: string;
  created_at: string;
  updated_at: string;
  retry_policy?: RetryPolicy;
  stats?: QueueStats;
}

export interface Project {
  id: string;
  organization_id: string;
  name: string;
  description?: string;
  created_at: string;
  queues_count?: number;
}

export interface Job {
  id: string;
  queue_id: string;
  queue_name?: string;
  job_type: string;
  payload: Record<string, any>;
  status: JobStatus;
  priority: number;
  scheduled_at?: string;
  available_at: string;
  attempts: number;
  max_attempts: number;
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

export interface JobExecution {
  id: string;
  job_id: string;
  worker_id?: string;
  attempt_number: number;
  status: string;
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
  error_message?: string;
}

export interface JobLog {
  id: string;
  job_id: string;
  execution_id?: string;
  level: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG';
  message: string;
  timestamp: string;
}

export interface DeadLetterEntry {
  id: string;
  job_id: string;
  reason: string;
  final_error?: string;
  failed_at: string;
  retry_count: number;
}

export interface JobDetail extends Job {
  executions: JobExecution[];
  logs: JobLog[];
  dead_letter?: DeadLetterEntry;
}

export interface Worker {
  id: string;
  worker_name: string;
  hostname: string;
  status: WorkerStatus;
  concurrency: number;
  last_heartbeat: string;
  started_at: string;
  stopped_at?: string;
  active_jobs: number;
  available_slots: number;
  is_stale: boolean;
}

export interface WorkerHeartbeat {
  id: string;
  worker_id: string;
  heartbeat_at: string;
  active_jobs: number;
  available_slots: number;
}

export interface MetricTimeSeriesPoint {
  timestamp: string;
  completed: number;
  failed: number;
  queued: number;
}

export interface OverviewMetrics {
  total_queues: number;
  total_jobs: number;
  queued_jobs: number;
  running_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  retrying_jobs: number;
  dead_letter_jobs: number;
  active_workers: number;
  total_workers: number;
  throughput_per_minute: number;
  success_rate: number;
  average_duration_ms: number;
  time_series: MetricTimeSeriesPoint[];
  job_type_distribution: Record<string, number>;
}

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}
