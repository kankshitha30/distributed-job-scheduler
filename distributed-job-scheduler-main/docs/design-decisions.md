# Distributed Job Scheduler - Architectural & Design Decisions

This document captures the engineering rationale, concurrency safety guarantees, trade-offs, and design patterns implemented across the Distributed Job Scheduling Platform.

---

## 1. Concurrency Safety: Atomic Job Claiming with `FOR UPDATE SKIP LOCKED`

### The Problem
When multiple distributed worker instances poll the database concurrently for work:
1. **Naive `SELECT` + `UPDATE`**: Two workers read the same `QUEUED` job simultaneously. Both workers update its status and execute the job concurrently, causing **duplicate side-effects** (e.g. charging a credit card twice).
2. **Naive `SELECT ... FOR UPDATE`**: Acquires exclusive row locks on matching records. However, when Worker 1 locks Job #1 and Job #2, Worker 2 **blocks and waits** until Worker 1's transaction commits. Under high concurrency, this creates severe database connection pool lock contention and serialized bottlenecks.

### The Solution: `FOR UPDATE SKIP LOCKED`
PostgreSQL provides `SKIP LOCKED` within row-level lock clauses:

```sql
SELECT id, queue_id, job_type, payload, attempts, max_attempts
FROM jobs
WHERE queue_id = :queue_id
  AND status IN ('QUEUED', 'RETRYING')
  AND available_at <= NOW()
ORDER BY priority DESC, available_at ASC
FOR UPDATE SKIP LOCKED
LIMIT :available_slots;
```

**Why this guarantees atomic, non-blocking claiming**:
- Worker 1 begins a transaction and locks the highest-priority eligible jobs (e.g. Jobs 1 & 2).
- Worker 2 begins a transaction concurrently. The database engine **instantly skips** Jobs 1 & 2 (which are currently locked by Worker 1) and locks the next available jobs (Jobs 3 & 4) without blocking.
- Each worker updates its claimed rows to `status = 'CLAIMED'`, inserts a `job_executions` record, and **immediately commits the transaction before starting job execution**.
- **Result**: Zero duplicate executions, zero lock contention, and linear horizontal throughput scaling across workers.

---

## 2. Why PostgreSQL for Job Scheduling?

1. **ACID Guarantees**: State transitions (`QUEUED` -> `CLAIMED` -> `RUNNING` -> `COMPLETED`) require transactional atomicity so that job claiming and execution logging never get out of sync.
2. **Transactional Outbox & Idempotency**: Jobs can be scheduled in the same atomic transaction as business data changes.
3. **Rich Querying & Aggregation**: Complex filtering, pagination, queue metrics, and retry policies are expressed cleanly in standard SQL with compound indexes.
4. **Relational Integrity**: Foreign key constraints with `CASCADE` and `SET NULL` behaviors keep executions, logs, and DLQ entries clean.

---

## 3. Why Separate Workers from API Gateway?

1. **Failure Domain Isolation**: Heavy CPU calculations or memory-intensive tasks in worker jobs do not impact API responsiveness or HTTP request handling.
2. **Independent Scalability**: The API gateway can be scaled based on ingress traffic, while worker instances can be scaled independently based on queue backlogs.
3. **Zero-Downtime Deployments**: Workers can drain running tasks gracefully during rolling updates without interrupting HTTP clients.

---

## 4. Why `asyncio` for Worker Execution?

- Rather than spawning an OS process or heavy thread per job, worker instances utilize Python's `asyncio` event loop.
- A configurable semaphore (`WORKER_CONCURRENCY`, default 5) manages concurrent execution tasks.
- I/O-bound operations (network requests, SMTP emails, DB logging) yield control cooperatively, achieving high concurrency with low memory footprint.

---

## 5. Why Separate `jobs` and `job_executions` Tables?

- A single job may undergo multiple retry attempts (e.g. Attempt 1 failed with timeout, Attempt 2 failed with connection error, Attempt 3 succeeded).
- Normalizing attempts into `job_executions` maintains an **immutable audit trail** of each attempt (worker ID, duration in milliseconds, error message, exact timestamps), preserving debugging telemetry.

---

## 6. Dead Letter Queue (DLQ) Isolation

- When a job exceeds its configured `max_attempts`, it transitions to `DEAD_LETTER` and an entry is recorded in `dead_letter_jobs`.
- **Reason**: Poison pills or broken payloads must not spin in endless retry loops consuming worker bandwidth.
- Isolating DLQ records allows operators to inspect the failure stack trace from the dashboard, fix downstream issues, and trigger manual requeuing (`POST /jobs/{job_id}/retry`).

---

## 7. Heartbeat Mechanism & Stale Worker Eviction

- Each worker daemon emits a heartbeat ping every 5 seconds to `worker_heartbeats` and updates `workers.last_heartbeat`.
- The poller runs an automatic stale detection check: if a worker's heartbeat is older than 15 seconds (e.g. process was killed with `SIGKILL` or host crashed), it is marked `OFFLINE`.
- This ensures dashboard operators always have accurate cluster visibility.

---

## 8. Graceful Shutdown Protocol

When a worker receives `SIGINT` (Ctrl+C) or `SIGTERM` (Docker stop):
1. Polling is stopped immediately (no new jobs are claimed).
2. The worker updates its database status to `STOPPING`.
3. Running asyncio tasks are given up to 30 seconds to finish in-flight work.
4. The worker updates its database status to `OFFLINE` with `stopped_at = NOW()`.
5. Database connection pools are cleanly disposed before process exit.

---

## 9. Limitations & Future Scaling Roadmap

1. **Database-as-Queue Throughput Ceiling**: PostgreSQL row locking scales well up to tens of thousands of jobs/min. For multi-million jobs/second, partition sharding or dedicated message brokers (e.g. Kafka, Redis Streams) can be layered underneath.
2. **Real-time Push Notifications**: The MVP uses 5s HTTP polling for simplicity and statelessness. WebSockets / Server-Sent Events (SSE) can be introduced for sub-second dashboard updates.
