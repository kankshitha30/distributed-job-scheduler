import uuid
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User, Organization, OrganizationMember
from app.utils.security import hash_password, verify_password, create_access_token
from app.middleware.error_handler import AppException
from fastapi import status


class AuthService:
    @staticmethod
    async def register(
        db: AsyncSession,
        email: str,
        password: str,
        name: str,
        organization_name: Optional[str] = None,
    ) -> Tuple[User, str, str]:
        # Check existing email
        stmt = select(User).where(User.email == email.lower().strip())
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise AppException(
                code="EMAIL_ALREADY_EXISTS",
                message="A user with this email already exists",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Create user
        user = User(
            id=str(uuid.uuid4()),
            email=email.lower().strip(),
            password_hash=hash_password(password),
            name=name.strip(),
        )
        db.add(user)
        await db.flush()

        # Create default organization if not specified
        org_name = organization_name.strip() if organization_name else f"{user.name}'s Workspace"
        org = Organization(
            id=str(uuid.uuid4()),
            name=org_name,
        )
        db.add(org)
        await db.flush()

        member = OrganizationMember(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            user_id=user.id,
            role="owner",
        )
        db.add(member)
        await db.commit()

        token = create_access_token({"sub": user.id, "email": user.email, "org_id": org.id})
        return user, org.id, token

    @staticmethod
    async def login(
        db: AsyncSession,
        email: str,
        password: str,
    ) -> Tuple[User, Optional[str], str]:
        stmt = select(User).where(User.email == email.lower().strip())
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            raise AppException(
                code="INVALID_CREDENTIALS",
                message="Invalid email or password",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        # Fetch primary organization
        stmt_org = select(OrganizationMember).where(OrganizationMember.user_id == user.id)
        res_org = await db.execute(stmt_org)
        member = res_org.scalars().first()
        org_id = member.organization_id if member else None

        token = create_access_token({"sub": user.id, "email": user.email, "org_id": org_id})
        return user, org_id, token


auth_service = AuthService()
