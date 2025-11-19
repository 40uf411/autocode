import pytest
from fastapi import status
from httpx import AsyncClient

from app.infrastructure.db.repositories import PrivilegeRepository, RoleRepository, UserRepository

FORM_HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}


async def login_and_get_token(client: AsyncClient, username: str, password: str) -> str:
    response = await client.post(
        "/auth/token",
        data={"username": username, "password": password},
        headers=FORM_HEADERS,
    )
    assert response.status_code == status.HTTP_200_OK
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_login_requires_user_not_blocked(client: AsyncClient, db_session) -> None:
    admin_token = await login_and_get_token(client, "admin@example.com", "ChangeMe123!")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    create_response = await client.post(
        "/users/",
        json={"email": "blocked@example.com", "password": "BlockMe123!"},
        headers=admin_headers,
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    user_id = create_response.json()["id"]

    block_response = await client.post(f"/users/{user_id}/block", headers=admin_headers)
    assert block_response.status_code == status.HTTP_200_OK

    response = await client.post(
        "/auth/token",
        data={"username": "blocked@example.com", "password": "BlockMe123!"},
        headers=FORM_HEADERS,
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_privilege_check_blocks_unauthorized_action(client: AsyncClient, db_session) -> None:
    privilege_repo = PrivilegeRepository(db_session)
    role_repo = RoleRepository(db_session)
    user_repo = UserRepository(db_session)

    read_privilege = await privilege_repo.get_or_create("users", "read")
    role = await role_repo.create("auditor")
    await role_repo.attach_privilege(role, read_privilege)
    await db_session.commit()

    user = await user_repo.create_user("auditor@example.com", "Audit123!", role_ids=[role.id])
    await db_session.commit()

    login_response = await client.post(
        "/auth/token",
        data={"username": "auditor@example.com", "password": "Audit123!"},
        headers=FORM_HEADERS,
    )
    assert login_response.status_code == status.HTTP_200_OK
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    forbidden_response = await client.post(
        "/users/",
        json={"email": "new@example.com", "password": "Strong123!"},
        headers=headers,
    )
    assert forbidden_response.status_code == status.HTTP_403_FORBIDDEN

    allowed_response = await client.get("/users/", headers=headers)
    assert allowed_response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_soft_deleted_user_cannot_login(client: AsyncClient) -> None:
    admin_token = await login_and_get_token(client, "admin@example.com", "ChangeMe123!")
    headers = {"Authorization": f"Bearer {admin_token}"}

    create_response = await client.post(
        "/users/",
        json={"email": "softdelete@example.com", "password": "Soft123!"},
        headers=headers,
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    user_id = create_response.json()["id"]

    delete_response = await client.delete(f"/users/{user_id}", headers=headers)
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    login_response = await client.post(
        "/auth/token",
        data={"username": "softdelete@example.com", "password": "Soft123!"},
        headers=FORM_HEADERS,
    )
    assert login_response.status_code == status.HTTP_401_UNAUTHORIZED
