from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User, OrganizationMember
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.services.project_service import project_service
from app.utils.security import get_current_user
from app.middleware.error_handler import AppException

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    req: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = req.organization_id
    if not org_id:
        stmt = select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
        res = await db.execute(stmt)
        member = res.scalars().first()
        if not member:
            raise AppException(
                code="NO_ORGANIZATION",
                message="User does not belong to any organization",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        org_id = member.organization_id

    project = await project_service.create_project(db, org_id, req)
    return ProjectResponse(
        id=project.id,
        organization_id=project.organization_id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        queues_count=0,
    )


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Fetch org ID of current user
    stmt = select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    res = await db.execute(stmt)
    members = list(res.scalars().all())
    org_ids = [m.organization_id for m in members]

    if not org_ids:
        return []

    # Get all projects for user's organizations
    all_projects = []
    for org_id in org_ids:
        projects = await project_service.list_projects(db, org_id)
        all_projects.extend(projects)
    return all_projects


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await project_service.get_project(db, project_id)
    return ProjectResponse(
        id=project.id,
        organization_id=project.organization_id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        queues_count=len(project.queues),
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    req: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await project_service.update_project(db, project_id, req)
    return ProjectResponse(
        id=project.id,
        organization_id=project.organization_id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        queues_count=len(project.queues),
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await project_service.delete_project(db, project_id)
    return None
