# Distributed Job Scheduler - Architecture Specification

This document details the high-level architecture, subsystem interactions, atomic job claiming protocol, worker task pool management, retry lifecycle, and Dead Letter Queue (DLQ) mechanics.

---

## 1. System Overview

```mermaid
graph TB
    subgraph "Client Layer"
        UI["React + Vite + TypeScript Dashboard<br>(Port 3000)"]
        CLI["External REST Clients / Scripts"]
    end

    subgraph "API Gateway & Control Plane"
        FastAPI["FastAPI REST API Service<br>(Uvicorn, Port 8000)"]
        AuthMiddleware["JWT Auth & Security Layer"]
        RouterLayer["Routers: /auth, /projects, /queues, /jobs, /workers, /metrics"]
    end

    subgraph "Storage & Coordination Layer"
        Postgres[(PostgreSQL 16 Engine)]
        JobTable[("jobs (MVCC Row Locking)")]
        ExecutionTable[("job_executions")]
        QueueTable[("queues")]
        WorkerTable[("workers & worker_heartbeats")]
        DLQTable[("dead_letter_jobs")]
    end

    subgraph "Distributed Worker Fleet"
        W1["Worker Instance 1<br>(asyncio Task Pool, Concurrency: 5)"]
        W2["Worker Instance 2<br>(asyncio Task Pool, Concurrency: 5)"]
        WN["Worker Instance N<br>(asyncio Task Pool, Concurrency: K)"]
    end

    UI -->|HTTP / REST Polling 5s| FastAPI
    CLI -->|HTTP / REST API| FastAPI
    FastAPI --> AuthMiddleware --> RouterLayer
    RouterLayer --> Postgres

    W1 -->|Atomic Claim: FOR UPDATE SKIP LOCKED| JobTable
    W2 -->|Atomic Claim: FOR UPDATE SKIP LOCKED| JobTable
    WN -->|Atomic Claim: FOR UPDATE SKIP LOCKED| JobTable

    W1 -->|Heartbeat every 5s| WorkerTable
    W2 -->|Heartbeat every 5s| WorkerTable
    WN -->|Heartbeat every 5s| WorkerTable

    W1 -->|Audit & Errors| ExecutionTable
    W1 -->|Max Retries Exhausted| DLQTable
```

---

## 2. Atomic Job Claiming Sequence

Multiple worker instances concurrently poll non-paused queues. The database transaction guarantees that **no two workers can ever claim the same job**.

```mermaid
sequenceDiagram
    autonumber
    participant W1 as Worker 1
    participant W2 as Worker 2
    participant DB as PostgreSQL Database

    Note over W1,W2: Both workers poll 'default' queue simultaneously
    W1->>DB: BEGIN TRANSACTION;
    W2->>DB: BEGIN TRANSACTION;

    W1->>DB: SELECT id, queue_id, ... FROM jobs<br/>WHERE queue_id = 'default' AND status IN ('QUEUED', 'RETRYING')<br/>AND available_at <= NOW()<br/>ORDER BY priority DESC, available_at ASC<br/>FOR UPDATE SKIP LOCKED LIMIT 2;
    Note over DB: Locks Rows #1 and #2 for W1

    W2->>DB: SELECT id, queue_id, ... FROM jobs<br/>WHERE queue_id = 'default' AND status IN ('QUEUED', 'RETRYING')<br/>AND available_at <= NOW()<br/>ORDER BY priority DESC, available_at ASC<br/>FOR UPDATE SKIP LOCKED LIMIT 2;
    Note over DB: Skips locked Rows #1 & #2, locks Rows #3 & #4 for W2

    W1->>DB: UPDATE jobs SET status = 'CLAIMED', attempts = attempts + 1 WHERE id IN (#1, #2);
    W1->>DB: INSERT INTO job_executions (job_id, worker_id, status) VALUES (#1, W1, 'RUNNING');
    W1->>DB: COMMIT;

    W2->>DB: UPDATE jobs SET status = 'CLAIMED', attempts = attempts + 1 WHERE id IN (#3, #4);
    W2->>DB: INSERT INTO job_executions (job_id, worker_id, status) VALUES (#3, W2, 'RUNNING');
    W2->>DB: COMMIT;

    Note over W1: Spawns asyncio Task for Job #1 & #2
    Note over W2: Spawns asyncio Task for Job #3 & #4
```

---

## 3. Complete Job State Machine

```mermaid
stateDiagram-v2
    [*] --> QUEUED : Immediate Job
    [*] --> SCHEDULED : Delayed / Future Scheduled

    SCHEDULED --> QUEUED : available_at <= NOW()

    QUEUED --> CLAIMED : Worker Atomic Claim (FOR UPDATE SKIP LOCKED)
    CLAIMED --> RUNNING : asyncio Task Begins Execution

    RUNNING --> COMPLETED : Handler Succeeded
    RUNNING --> FAILED : Handler Raised Exception

    FAILED --> RETRYING : attempts < max_attempts<br/>(Calculates Delay: Fixed/Linear/Exponential)
    RETRYING --> QUEUED : available_at <= NOW()

    FAILED --> DEAD_LETTER : attempts >= max_attempts<br/>(Records in dead_letter_jobs)

    DEAD_LETTER --> QUEUED : Manual Admin Requeue (POST /jobs/:id/retry)
    COMPLETED --> [*]
```

---

## 4. Subsystem Responsibilities

### 1. API Control Plane (FastAPI)
- **Authentication**: JWT token issuance and validation, bcrypt password hashing.
- **Queue Administration**: Concurrency limits, priority hierarchy, pause/resume switches.
- **Job Ingestion**: Immediate, delayed, cron recurring, batch ingestion with idempotency checking.
- **Telemetry Aggregation**: Queue metrics, execution latencies, worker health status.

### 2. Distributed Worker Service (asyncio Daemon)
- **Self-Registration**: Registers worker metadata (hostname, PID, concurrency) on startup.
- **Heartbeat Loop**: Emits heartbeat every 5s recording active coroutines and remaining slots.
- **Queue Polling & Concurrency Protection**: Computes available worker capacity and respects per-queue limits before claiming.
- **Job Execution Abstraction**: Routes job payloads to dedicated `JobExecutor` implementations (`echo`, `sleep`, `calculation`, `email_simulation`, `intentional_failure`).
- **Dead Letter Escalation**: Automatically routes exhausted jobs to DLQ upon retry limit exhaustion.
- **Graceful Shutdown**: Intercepts `SIGINT`/`SIGTERM`, stops polling, drains running tasks, sets status to `STOPPING` then `OFFLINE`.

### 3. Recurring Cron Scheduler
- Periodically checks `scheduled_jobs` table for active cron expressions whose `next_run_at <= NOW()`.
- Enqueues fresh `Job` instances into the target queue and computes next execution timestamp via `croniter`.
