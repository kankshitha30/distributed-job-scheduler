import axios from 'axios';
import {
  AuthResponse,
  User,
  Project,
  Queue,
  QueueStats,
  Job,
  JobDetail,
  Worker,
  WorkerHeartbeat,
  OverviewMetrics,
  PaginatedResponse,
  RetryPolicy,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach Authorization Bearer Token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Intercept 401 Unauthorized
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !window.location.pathname.includes('/login')) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const api = {
  // Auth
  register: async (data: { email: string; password: string; name: string; organization_name?: string }) => {
    const res = await apiClient.post<AuthResponse>('/auth/register', data);
    return res.data;
  },
  login: async (data: { email: string; password: string }) => {
    const res = await apiClient.post<AuthResponse>('/auth/login', data);
    return res.data;
  },
  getMe: async () => {
    const res = await apiClient.get<User>('/auth/me');
    return res.data;
  },

  // Projects
  getProjects: async () => {
    const res = await apiClient.get<Project[]>('/projects');
    return res.data;
  },
  createProject: async (data: { name: string; description?: string }) => {
    const res = await apiClient.post<Project>('/projects', data);
    return res.data;
  },

  // Queues
  getQueues: async () => {
    const res = await apiClient.get<Queue[]>('/queues');
    return res.data;
  },
  getProjectQueues: async (projectId: string) => {
    const res = await apiClient.get<Queue[]>(`/projects/${projectId}/queues`);
    return res.data;
  },
  getQueue: async (queueId: string) => {
    const res = await apiClient.get<Queue>(`/queues/${queueId}`);
    return res.data;
  },
  createQueue: async (projectId: string, data: { name: string; priority: number; concurrency_limit: number; retry_policy_id?: string }) => {
    const res = await apiClient.post<Queue>(`/projects/${projectId}/queues`, data);
    return res.data;
  },
  updateQueue: async (queueId: string, data: Partial<Queue>) => {
    const res = await apiClient.put<Queue>(`/queues/${queueId}`, data);
    return res.data;
  },
  pauseQueue: async (queueId: string) => {
    const res = await apiClient.post<Queue>(`/queues/${queueId}/pause`);
    return res.data;
  },
  resumeQueue: async (queueId: string) => {
    const res = await apiClient.post<Queue>(`/queues/${queueId}/resume`);
    return res.data;
  },
  deleteQueue: async (queueId: string) => {
    await apiClient.delete(`/queues/${queueId}`);
  },
  getQueueStats: async (queueId: string) => {
    const res = await apiClient.get<QueueStats>(`/queues/${queueId}/stats`);
    return res.data;
  },
  getQueueDeadLetters: async (queueId: string, page = 1, pageSize = 20) => {
    const res = await apiClient.get<PaginatedResponse<Job>>(`/queues/${queueId}/dead-letter?page=${page}&page_size=${pageSize}`);
    return res.data;
  },

  // Jobs
  getJobs: async (params?: {
    queue_id?: string;
    status?: string;
    job_type?: string;
    priority?: number;
    worker_id?: string;
    page?: number;
    page_size?: number;
  }) => {
    const res = await apiClient.get<PaginatedResponse<Job>>('/jobs', { params });
    return res.data;
  },
  getJob: async (jobId: string) => {
    const res = await apiClient.get<JobDetail>(`/jobs/${jobId}`);
    return res.data;
  },
  createJob: async (queueId: string, data: {
    job_type: string;
    payload: Record<string, any>;
    priority?: number;
    delay_seconds?: number;
    scheduled_at?: string;
    cron_expression?: string;
    max_attempts?: number;
  }, idempotencyKey?: string) => {
    const headers: Record<string, string> = {};
    if (idempotencyKey) {
      headers['Idempotency-Key'] = idempotencyKey;
    }
    const res = await apiClient.post<Job>(`/queues/${queueId}/jobs`, data, { headers });
    return res.data;
  },
  createBatchJobs: async (queueId: string, jobs: Array<{
    job_type: string;
    payload: Record<string, any>;
    priority?: number;
    delay_seconds?: number;
    scheduled_at?: string;
    max_attempts?: number;
  }>) => {
    const res = await apiClient.post<Job[]>(`/queues/${queueId}/jobs/batch`, { jobs });
    return res.data;
  },
  retryJob: async (jobId: string) => {
    const res = await apiClient.post<JobDetail>(`/jobs/${jobId}/retry`);
    return res.data;
  },

  // Workers
  getWorkers: async () => {
    const res = await apiClient.get<Worker[]>('/workers');
    return res.data;
  },
  getWorker: async (workerId: string) => {
    const res = await apiClient.get<Worker>(`/workers/${workerId}`);
    return res.data;
  },
  getWorkerHeartbeats: async (workerId: string, limit = 50) => {
    const res = await apiClient.get<WorkerHeartbeat[]>(`/workers/${workerId}/heartbeats?limit=${limit}`);
    return res.data;
  },

  // Retry Policies
  getRetryPolicies: async () => {
    const res = await apiClient.get<RetryPolicy[]>('/retry-policies');
    return res.data;
  },
  createRetryPolicy: async (data: Omit<RetryPolicy, 'id'>) => {
    const res = await apiClient.post<RetryPolicy>('/retry-policies', data);
    return res.data;
  },

  // Metrics
  getMetricsOverview: async () => {
    const res = await apiClient.get<OverviewMetrics>('/metrics/overview');
    return res.data;
  },
};
