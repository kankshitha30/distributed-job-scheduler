# Distributed Job Scheduler - REST API Reference

All protected endpoints require an `Authorization: Bearer <JWT_TOKEN>` header.

Interactive OpenAPI Swagger UI is available at:
`http://localhost:8000/docs`

---

## 1. Standard Error Envelope

All API errors return a consistent structured JSON envelope:

```json
{
  "error": {
    "code": "QUEUE_NOT_FOUND",
    "message": "Queue with ID 85cbf5ea-8a60-4e7a-930b-e4e373aa9365 does not exist"
  }
}
```

Common Error Codes:
- `UNAUTHORIZED`: Missing or malformed token
- `INVALID_TOKEN`: Token expired or signature invalid
- `NOT_FOUND`: Resource could not be found
- `VALIDATION_ERROR`: Missing or invalid request fields
- `QUEUE_ALREADY_EXISTS`: Duplicate queue name in project
- `INVALID_STATE`: Operation not allowed in current state

---

## 2. Authentication Endpoints

### `POST /auth/register`
Creates a user account, default workspace organization, and returns an access token.

**Request Body:**
```json
{
  "email": "dev@example.com",
  "password": "securepassword123",
  "name": "Alex Smith",
  "organization_name": "Acme Inc"
}
```

**Response (201 Created):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "902d1844-32aa-4cfa-93e1-8889da3b2c12",
  "email": "dev@example.com",
  "name": "Alex Smith",
  "organization_id": "18f92110-3882-4aa8-bc19-aa8127361819"
}
```

### `POST /auth/login`
Authenticates user credentials and issues a JWT token.

**Request Body:**
```json
{
  "email": "dev@example.com",
  "password": "securepassword123"
}
```

### `GET /auth/me`
Returns current authenticated user profile.

---

## 3. Project Management

- `GET /projects`: List user projects
- `POST /projects`: Create a new project (`{ "name": "Payment Service", "description": "..." }`)
- `GET /projects/{id}`: Get project details
- `PUT /projects/{id}`: Update project metadata
- `DELETE /projects/{id}`: Delete project (Cascade deletes queues & jobs)

---

## 4. Queue Management

### `POST /projects/{project_id}/queues`
Creates a new queue within a project.

**Request Body:**
```json
{
  "name": "invoices",
  "priority": 10,
  "concurrency_limit": 5,
  "retry_policy_id": "policy-uuid-here"
}
```

### `GET /queues`
Lists all queues across user organizations with aggregated statistics.

### `GET /queues/{queue_id}`
Returns details of a specific queue.

### `POST /queues/{queue_id}/pause`
Pauses the queue. Workers will immediately stop polling and claiming new jobs from this queue.

### `POST /queues/{queue_id}/resume`
Resumes the queue for worker claiming.

### `GET /queues/{queue_id}/stats`
Returns aggregated real-time metrics:
```json
{
  "total_jobs": 120,
  "queued_jobs": 4,
  "running_jobs": 2,
  "completed_jobs": 108,
  "failed_jobs": 4,
  "retrying_jobs": 1,
  "dead_letter_jobs": 1,
  "average_execution_time_ms": 234.5,
  "success_rate": 95.58
}
```

### `GET /queues/{queue_id}/dead-letter`
Returns paginated list of permanently failed jobs in this queue.

---

## 5. Job Operations

### `POST /queues/{queue_id}/jobs`
Submits a background job. Supports idempotency key header.

**Headers:**
- `Idempotency-Key`: `(Optional string, e.g. tx-99248)`

**Request Body Options:**
```json
// 1. Immediate Execution
{
  "job_type": "email_simulation",
  "payload": { "to": "user@example.com", "subject": "Welcome" },
  "priority": 5
}

// 2. Delayed Execution
{
  "job_type": "sleep",
  "payload": { "seconds": 5 },
  "delay_seconds": 60
}

// 3. Future Scheduled Execution
{
  "job_type": "calculation",
  "payload": { "operation": "fibonacci", "n": 30 },
  "scheduled_at": "2026-08-20T10:00:00Z"
}

// 4. Recurring Cron Execution
{
  "job_type": "echo",
  "payload": { "message": "Hourly health check" },
  "cron_expression": "0 * * * *"
}
```

### `POST /queues/{queue_id}/jobs/batch`
Enqueues multiple jobs atomically in one API request:
```json
{
  "jobs": [
    { "job_type": "echo", "payload": { "index": 1 } },
    { "job_type": "echo", "payload": { "index": 2 } }
  ]
}
```

### `GET /jobs`
Paginated search & filter endpoint.

**Query Parameters:**
- `queue_id`: Filter by queue UUID
- `status`: `QUEUED | SCHEDULED | CLAIMED | RUNNING | COMPLETED | FAILED | RETRYING | DEAD_LETTER`
- `job_type`: `echo | sleep | calculation | email_simulation | intentional_failure`
- `priority`: Integer priority level
- `page`: Page number (default 1)
- `page_size`: Page size (default 20, max 100)

**Response:**
```json
{
  "items": [ ... ],
  "page": 1,
  "page_size": 20,
  "total": 54,
  "total_pages": 3
}
```

### `GET /jobs/{job_id}`
Returns complete job details including payload, execution attempts, logs, and DLQ diagnostics.

### `POST /jobs/{job_id}/retry`
Manually requeues a `DEAD_LETTER` or `FAILED` job back into `QUEUED` state.

### `GET /jobs/{job_id}/executions`
Returns attempt execution history with timestamps, worker IDs, and durations.

### `GET /jobs/{job_id}/logs`
Returns real-time execution logs for a job.

---

## 6. Workers & Metrics

- `GET /workers`: List active and offline worker instances
- `GET /workers/{worker_id}`: Get worker status & capacity
- `GET /workers/{worker_id}/heartbeats`: Get recent heartbeat history (5s intervals)
- `GET /metrics/overview`: High-level dashboard telemetry and time-series points
