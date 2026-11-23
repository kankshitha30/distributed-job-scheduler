import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_job_creation_and_lifecycle(client: AsyncClient, auth_headers: dict):
    # Setup project and queue
    p_resp = await client.post("/projects", json={"name": "Job Test Project"}, headers=auth_headers)
    p_id = p_resp.json()["id"]

    q_resp = await client.post(
        f"/projects/{p_id}/queues",
        json={"name": "test-work-queue", "priority": 1, "concurrency_limit": 5},
        headers=auth_headers,
    )
    q_id = q_resp.json()["id"]

    # 1. Create Immediate Job
    job_resp = await client.post(
        f"/queues/{q_id}/jobs",
        json={
            "job_type": "echo",
            "payload": {"message": "Immediate Job Test"},
            "priority": 10,
        },
        headers=auth_headers,
    )
    assert job_resp.status_code == 201
    job_data = job_resp.json()
    assert job_data["status"] == "QUEUED"
    assert job_data["priority"] == 10
    job_id = job_data["id"]

    # 2. Create Delayed Job
    delayed_resp = await client.post(
        f"/queues/{q_id}/jobs",
        json={
            "job_type": "sleep",
            "payload": {"seconds": 1},
            "delay_seconds": 60,
        },
        headers=auth_headers,
    )
    assert delayed_resp.status_code == 201
    assert delayed_resp.json()["status"] == "SCHEDULED"

    # 3. Create Batch Jobs
    batch_resp = await client.post(
        f"/queues/{q_id}/jobs/batch",
        json={
            "jobs": [
                {"job_type": "echo", "payload": {"item": 1}},
                {"job_type": "echo", "payload": {"item": 2}},
                {"job_type": "calculation", "payload": {"operation": "fibonacci", "n": 10}},
            ]
        },
        headers=auth_headers,
    )
    assert batch_resp.status_code == 201
    assert len(batch_resp.json()) == 3

    # 4. Idempotency Test
    idem_headers = {**auth_headers, "Idempotency-Key": "unique-idem-key-12345"}
    first_resp = await client.post(
        f"/queues/{q_id}/jobs",
        json={"job_type": "echo", "payload": {"data": "first_call"}},
        headers=idem_headers,
    )
    assert first_resp.status_code == 201
    first_id = first_resp.json()["id"]

    second_resp = await client.post(
        f"/queues/{q_id}/jobs",
        json={"job_type": "echo", "payload": {"data": "second_call"}},
        headers=idem_headers,
    )
    assert second_resp.status_code == 201
    assert second_resp.json()["id"] == first_id

    # 5. List and Filter Jobs
    list_resp = await client.get(f"/jobs?queue_id={q_id}&page=1&page_size=10", headers=auth_headers)
    assert list_resp.status_code == 200
    res_json = list_resp.json()
    assert res_json["total"] >= 5
    assert len(res_json["items"]) >= 5

    # 6. Job Details & Logs
    detail_resp = await client.get(f"/jobs/{job_id}", headers=auth_headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == job_id
    assert len(detail_resp.json()["logs"]) >= 1
