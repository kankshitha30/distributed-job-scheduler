import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    # 1. Register new user
    reg_payload = {
        "email": "newuser@example.com",
        "password": "strongpassword123",
        "name": "New User",
        "organization_name": "Test Startup",
    }
    reg_resp = await client.post("/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201
    data = reg_resp.json()
    assert "access_token" in data
    assert data["email"] == "newuser@example.com"
    token = data["access_token"]

    # 2. Login with correct credentials
    login_resp = await client.post(
        "/auth/login",
        json={"email": "newuser@example.com", "password": "strongpassword123"},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()

    # 3. Login with wrong password
    bad_login = await client.post(
        "/auth/login",
        json={"email": "newuser@example.com", "password": "wrongpassword"},
    )
    assert bad_login.status_code == 401
    assert bad_login.json()["error"]["code"] == "INVALID_CREDENTIALS"

    # 4. Get Current User (/auth/me)
    me_resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "newuser@example.com"

    # 5. Access /auth/me without token
    unauth_resp = await client.get("/auth/me")
    assert unauth_resp.status_code == 401
