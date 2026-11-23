# Distributed Job Scheduler - Database Schema & ER Model

This document outlines the relational database architecture, Entity Relationship (ER) diagram, primary/foreign key constraints, cascade rules, and query optimization indexing strategies.

---

## 1. Entity Relationship (ER) Diagram

```mermaid
erDiagram
    users ||--o{ organization_members : "belongs to"
    organizations ||--o{ organization_members : "has"
    organizations ||--o{ projects : "contains"
    projects ||--o{ queues : "owns"
    retry_policies ||--o{ queues : "governs"
    queues ||--o{ jobs : "enqueues"
    queues ||--o{ scheduled_jobs : "schedules"
    jobs ||--o{ job_executions : "executes"
    jobs ||--o{ job_logs : "records"
    jobs ||--o| dead_letter_jobs : "escalates to"
    workers ||--o{ worker_heartbeats : "emits"
    workers ||--o{ job_executions : "processes"
    job_executions ||--o{ job_logs : "streams"

    users {
        string id PK
        string email UK
        string password_hash
        string name
        datetime created_at
    }

    organizations {
        string id PK
        string name
        datetime created_at
    }

    organization_members {
        string id PK
        string organization_id FK
        string user_id FK
        string role
        datetime created_at
    }

    projects {
        string id PK
        string organization_id FK
        string name
        text description
        datetime created_at
    }

    retry_policies {
        string id PK
        string name
        string strategy
        int max_attempts
        int initial_delay_seconds
        float backoff_multiplier
    }

    queues {
        string id PK
        string project_id FK
        string name
        int priority
        int concurrency_limit
        boolean paused
        string retry_policy_id FK
        datetime created_at
        datetime updated_at
    }

    jobs {
        string id PK
        string queue_id FK
        string job_type
        json payload
        string status
        int priority
        datetime scheduled_at
        datetime available_at
        int attempts
        int max_attempts
        string idempotency_key UK
        datetime created_at
        datetime updated_at
        datetime completed_at
    }

    job_executions {
        string id PK
        string job_id FK
        string worker_id FK
        int attempt_number
        string status
        datetime started_at
        datetime completed_at
        int duration_ms
        text error_message
    }

    job_logs {
        string id PK
        string job_id FK
        string execution_id FK
        string level
        text message
        datetime timestamp
    }

    scheduled_jobs {
        string id PK
        string queue_id FK
        string job_type
        json payload
        string cron_expression
        datetime next_run_at
        boolean enabled
        datetime created_at
    }

    dead_letter_jobs {
        string id PK
        string job_id FK "UK"
        string reason
        text final_error
        datetime failed_at
        int retry_count
    }

    workers {
        string id PK
        string worker_name
        string hostname
        string status
        int concurrency
        datetime last_heartbeat
        datetime started_at
        datetime stopped_at
    }

    worker_heartbeats {
        string id PK
        string worker_id FK
        datetime heartbeat_at
        int active_jobs
        int available_slots
    }
```

---

## 2. Table Specifications & Foreign Key Cascades

| Table | Target FK | On Delete Behavior | Rationale |
| :--- | :--- | :--- | :--- |
| `organization_members` | `organizations(id)`, `users(id)` | `CASCADE` | Deleting a user or organization purges membership mappings. |
| `projects` | `organizations(id)` | `CASCADE` | Deleting an organization deletes associated projects. |
| `queues` | `projects(id)` | `CASCADE` | Deleting a project purges its queues. |
| `queues` | `retry_policies(id)` | `SET NULL` | Deleting a retry policy sets queue policy to null without deleting queues. |
| `jobs` | `queues(id)` | `CASCADE` | Deleting a queue deletes all queued/completed jobs in it. |
| `job_executions` | `jobs(id)` | `CASCADE` | Deleting a job removes execution records. |
| `job_executions` | `workers(id)` | `SET NULL` | Terminating or deleting a worker preserves execution audit records. |
| `job_logs` | `jobs(id)` | `CASCADE` | Deleting a job cleans up log traces. |
| `dead_letter_jobs` | `jobs(id)` | `CASCADE` | Requeuing or removing a job purges DLQ entries. |
| `worker_heartbeats` | `workers(id)` | `CASCADE` | Purging worker removes historical heartbeats. |

---

## 3. Query Optimization Indexes

```sql
-- 1. Atomic claiming query optimization
CREATE INDEX idx_jobs_queue_priority_available ON jobs(queue_id, priority DESC, available_at ASC);

-- 2. Status & availability lookups for queue poller
CREATE INDEX idx_jobs_queue_status ON jobs(queue_id, status);
CREATE INDEX idx_jobs_status_available ON jobs(status, available_at);

-- 3. Execution history lookups
CREATE INDEX idx_job_executions_job_id ON job_executions(job_id);

-- 4. Job log time-series ordering
CREATE INDEX idx_job_logs_job_timestamp ON job_logs(job_id, timestamp);

-- 5. Worker heartbeat freshness lookups
CREATE INDEX idx_worker_heartbeats_worker_time ON worker_heartbeats(worker_id, heartbeat_at DESC);

-- 6. Recurring cron lookups
CREATE INDEX idx_scheduled_jobs_next_run ON scheduled_jobs(next_run_at);

-- 7. Unique constraints
CREATE UNIQUE INDEX idx_queues_project_name ON queues(project_id, name);
CREATE UNIQUE INDEX idx_jobs_idempotency ON jobs(idempotency_key) WHERE idempotency_key IS NOT NULL;
```
