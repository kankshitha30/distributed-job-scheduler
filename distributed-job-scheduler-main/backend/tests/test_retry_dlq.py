import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.job_service import job_service
from app.models import Job, DeadLetterJob, Queue, Project


def test_retry_delay_calculations():
    # Fixed: initial_delay=5
    assert job_service.calculate_retry_delay("fixed", 1, 5, 2.0) == 5
    assert job_service.calculate_retry_delay("fixed", 2, 5, 2.0) == 5
    assert job_service.calculate_retry_delay("fixed", 3, 5, 2.0) == 5

    # Linear: initial_delay=5 (delay = 5 * attempt)
    assert job_service.calculate_retry_delay("linear", 1, 5, 2.0) == 5
    assert job_service.calculate_retry_delay("linear", 2, 5, 2.0) == 10
    assert job_service.calculate_retry_delay("linear", 3, 5, 2.0) == 15

    # Exponential: initial_delay=5, multiplier=2.0 (delay = 5 * (2^(attempt-1)))
    assert job_service.calculate_retry_delay("exponential", 1, 5, 2.0) == 5
    assert job_service.calculate_retry_delay("exponential", 2, 5, 2.0) == 10
    assert job_service.calculate_retry_delay("exponential", 3, 5, 2.0) == 20
    assert job_service.calculate_retry_delay("exponential", 4, 5, 2.0) == 40


@pytest.mark.asyncio
async def test_dead_letter_queue_and_manual_retry(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    # Setup project and queue
    now = datetime.now(timezone.utc)
    proj = Project(id=str(uuid.uuid4()), organization_id="test-org-id-1234", name="DLQ Project", created_at=now)
    q = Queue(id=str(uuid.uuid4()), project_id=proj.id, name="dlq-test-queue", priority=0, concurrency_limit=5, created_at=now, updated_at=now)
    db_session.add_all([proj, q])
    await db_session.flush()

    # Create a job in DEAD_LETTER state
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        queue_id=q.id,
        job_type="intentional_failure",
        payload={"error": "Failed 3 times"},
        status="DEAD_LETTER",
        priority=0,
        available_at=now,
        attempts=3,
        max_attempts=3,
        created_at=now,
        updated_at=now,
    )
    dlq_entry = DeadLetterJob(
        id=str(uuid.uuid4()),
        job_id=job_id,
        reason="Exhausted maximum retry attempts (3)",
        final_error="Intentional failure simulated",
        failed_at=now,
        retry_count=3,
    )
    db_session.add_all([job, dlq_entry])
    await db_session.commit()

    # 1. Fetch Dead Letter Queue
    dlq_resp = await client.get(f"/queues/{q.id}/dead-letter", headers=auth_headers)
    assert dlq_resp.status_code == 200
    dlq_items = dlq_resp.json()["items"]
    assert len(dlq_items) == 1
    assert dlq_items[0]["id"] == job_id
    assert dlq_items[0]["status"] == "DEAD_LETTER"

    # 2. Retry the Dead Letter Job
    retry_resp = await client.post(f"/jobs/{job_id}/retry", headers=auth_headers)
    assert retry_resp.status_code == 200
    retried_job = retry_resp.json()
    assert retried_job["status"] == "QUEUED"
    assert retried_job["attempts"] == 0
    assert retried_job["dead_letter"] is None

    # 3. Verify it is no longer in the DLQ endpoint
    dlq_after = await client.get(f"/queues/{q.id}/dead-letter", headers=auth_headers)
    assert dlq_after.status_code == 200
    assert len(dlq_after.json()["items"]) == 0
