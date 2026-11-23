import uuid
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.worker_service import worker_service
from app.models.worker import Worker


@pytest.mark.asyncio
async def test_worker_registration_and_heartbeats(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    worker_id = str(uuid.uuid4())
    worker_name = "test-worker-alpha"
    
    # 1. Register worker
    w = await worker_service.register_worker(
        db=db_session,
        worker_id=worker_id,
        worker_name=worker_name,
        hostname="node-1.internal",
        concurrency=4,
    )
    assert w.status == "ONLINE"
    assert w.concurrency == 4

    # 2. Record Heartbeat
    await worker_service.record_heartbeat(
        db=db_session,
        worker_id=worker_id,
        active_jobs=2,
        available_slots=2,
    )

    # 3. Fetch workers via REST API
    workers_resp = await client.get("/workers", headers=auth_headers)
    assert workers_resp.status_code == 200
    workers = workers_resp.json()
    assert len(workers) >= 1
    target = next((x for x in workers if x["id"] == worker_id), None)
    assert target is not None
    assert target["worker_name"] == worker_name
    assert target["status"] == "ONLINE"
    assert target["active_jobs"] == 2
    assert target["available_slots"] == 2

    # 4. Fetch Heartbeat History via REST API
    hb_resp = await client.get(f"/workers/{worker_id}/heartbeats", headers=auth_headers)
    assert hb_resp.status_code == 200
    assert len(hb_resp.json()) >= 1


@pytest.mark.asyncio
async def test_stale_worker_detection(db_session: AsyncSession):
    worker_id = str(uuid.uuid4())
    stale_time = datetime.now(timezone.utc) - timedelta(seconds=30)
    
    stale_worker = Worker(
        id=worker_id,
        worker_name="stale-worker-99",
        hostname="crashed-node",
        status="ONLINE",
        concurrency=5,
        last_heartbeat=stale_time,
        started_at=stale_time,
    )
    db_session.add(stale_worker)
    await db_session.commit()

    # Trigger stale detection with 15s threshold
    marked_count = await worker_service.mark_stale_workers(db_session, timeout_seconds=15.0)
    assert marked_count == 1

    # Verify status changed to OFFLINE
    w_info = await worker_service.get_worker(db_session, worker_id)
    assert w_info.status == "OFFLINE"
