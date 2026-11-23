import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from fastapi import status

from app.models.project import Project, Queue
from app.models.user import Organization
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.middleware.error_handler import AppException


class ProjectService:
    @staticmethod
    async def create_project(
        db: AsyncSession,
        organization_id: str,
        data: ProjectCreate,
    ) -> Project:
        # Check org exists
        org_res = await db.execute(select(Organization).where(Organization.id == organization_id))
        if not org_res.scalar_one_or_none():
            raise AppException(
                code="ORGANIZATION_NOT_FOUND",
                message=f"Organization {organization_id} does not exist",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        project = Project(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            name=data.name.strip(),
            description=data.description.strip() if data.description else None,
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return project

    @staticmethod
    async def get_project(db: AsyncSession, project_id: str) -> Project:
        stmt = (
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.queues))
        )
        res = await db.execute(stmt)
        project = res.scalar_one_or_none()
        if not project:
            raise AppException(
                code="PROJECT_NOT_FOUND",
                message=f"Project with ID {project_id} does not exist",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return project

    @staticmethod
    async def list_projects(db: AsyncSession, organization_id: Optional[str] = None) -> List[ProjectResponse]:
        stmt = select(Project).options(selectinload(Project.queues))
        if organization_id:
            stmt = stmt.where(Project.organization_id == organization_id)
        stmt = stmt.order_by(Project.created_at.desc())

        res = await db.execute(stmt)
        projects = list(res.scalars().all())

        return [
            ProjectResponse(
                id=p.id,
                organization_id=p.organization_id,
                name=p.name,
                description=p.description,
                created_at=p.created_at,
                queues_count=len(p.queues),
            )
            for p in projects
        ]

    @staticmethod
    async def update_project(db: AsyncSession, project_id: str, data: ProjectUpdate) -> Project:
        project = await ProjectService.get_project(db, project_id)
        if data.name is not None:
            project.name = data.name.strip()
        if data.description is not None:
            project.description = data.description.strip() if data.description else None

        await db.commit()
        await db.refresh(project)
        return project

    @staticmethod
    async def delete_project(db: AsyncSession, project_id: str) -> None:
        project = await ProjectService.get_project(db, project_id)
        await db.delete(project)
        await db.commit()


project_service = ProjectService()
