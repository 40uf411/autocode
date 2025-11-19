from sqlalchemy import select

from app.infrastructure.db.repositories import (
    PrivilegeRepository,
    RoleORM,
    RoleRepository,
    UserRepository,
)
from app.infrastructure.db.session import get_session_maker


async def seed_initial_data() -> None:
    session_factory = get_session_maker()
    async with session_factory() as session:
        privilege_repo = PrivilegeRepository(session)
        role_repo = RoleRepository(session)
        user_repo = UserRepository(session)

        privilege_specs = [
            ("users", "read"),
            ("users", "insert"),
            ("users", "update"),
            ("users", "delete"),
            ("users", "block"),
            ("users", "unblock"),
            ("users", "reset_password"),
            ("roles", "read"),
            ("roles", "insert"),
            ("roles", "update"),
            ("roles", "delete"),
            ("privileges", "read"),
            ("privileges", "insert"),
            ("privileges", "update"),
            ("privileges", "delete"),
        ]
        privileges = []
        for resource, action in privilege_specs:
            privilege = await privilege_repo.get_or_create(resource, action)
            privileges.append(privilege)

        admin_role = await role_repo.get_by_name("admin")
        if not admin_role:
            admin_role = await role_repo.create("admin", is_superuser=True)
            for privilege in privileges:
                await role_repo.attach_privilege(admin_role, privilege)

        admin_user = await user_repo.get_by_email("admin@example.com")
        if not admin_user:
            await user_repo.create_user(
                email="admin@example.com",
                password="ChangeMe123!",
                role_ids=[admin_role.id] if admin_role.id else None,
            )
        await session.commit()
