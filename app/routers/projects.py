from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List as TypingList
from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/", response_model=schemas.Project)
async def create_project(project: schemas.ProjectCreate, db: AsyncSession = Depends(get_db)):
    """Create a new project"""
    db_project = models.Project(name=project.name)
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)
    return db_project


@router.get("/", response_model=TypingList[schemas.Project])
async def get_projects(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Get all projects"""
    result = await db.execute(select(models.Project).offset(skip).limit(limit))
    projects = result.scalars().all()
    return projects


@router.get("/{project_id}", response_model=schemas.Project)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific project"""
    result = await db.execute(select(models.Project).filter(models.Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=schemas.Project)
async def rename_project(project_id: int, project_update: schemas.ProjectUpdate, db: AsyncSession = Depends(get_db)):
    """Rename a project"""
    result = await db.execute(select(models.Project).filter(models.Project.id == project_id))
    db_project = result.scalar_one_or_none()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db_project.name = project_update.name
    await db.commit()
    await db.refresh(db_project)
    return db_project


@router.delete("/{project_id}")
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a project"""
    result = await db.execute(select(models.Project).filter(models.Project.id == project_id))
    db_project = result.scalar_one_or_none()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(db_project)
    await db.commit()
    return {"message": "Project deleted successfully"}
