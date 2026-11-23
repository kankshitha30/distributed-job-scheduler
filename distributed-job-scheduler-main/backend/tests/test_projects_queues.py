import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_projects_and_queues_crud(client: AsyncClient, auth_headers: dict):
    # 1. Create Retry Policy
    rp_resp = await client.post(
        "/retry-policies",
        json={
            "name": "Test Exponential Policy",
            "strategy": "exponential",
            "max_attempts": 4,
            "initial_delay_seconds": 2,
            "backoff_multiplier": 2.0,
        },
        headers=auth_headers,
    )
    assert rp_resp.status_code == 201
    policy_id = rp_resp.json()["id"]

    # 2. Create Project
    proj_resp = await client.post(
        "/projects",
        json={"name": "Billing Service", "description": "Processes payment jobs"},
        headers=auth_headers,
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]
    assert proj_resp.json()["name"] == "Billing Service"

    # 3. Create Queue
    q_resp = await client.post(
        f"/projects/{project_id}/queues",
        json={
            "name": "invoices",
            "priority": 5,
            "concurrency_limit": 3,
            "retry_policy_id": policy_id,
        },
        headers=auth_headers,
    )
    assert q_resp.status_code == 201
    queue_id = q_resp.json()["id"]
    assert q_resp.json()["name"] == "invoices"
    assert q_resp.json()["paused"] is False

    # 4. Pause Queue
    pause_resp = await client.post(f"/queues/{queue_id}/pause", headers=auth_headers)
    assert pause_resp.status_code == 200
    assert pause_resp.json()["paused"] is True

    # 5. Resume Queue
    resume_resp = await client.post(f"/queues/{queue_id}/resume", headers=auth_headers)
    assert resume_resp.status_code == 200
    assert resume_resp.json()["paused"] is False

    # 6. Get Queue Stats
    stats_resp = await client.get(f"/queues/{queue_id}/stats", headers=auth_headers)
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_jobs"] == 0
    assert stats["queued_jobs"] == 0

    # 7. List Queues
    list_q = await client.get("/queues", headers=auth_headers)
    assert list_q.status_code == 200
    assert len(list_q.json()) >= 1
