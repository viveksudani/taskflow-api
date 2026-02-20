from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List as TypingList
from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/lists", tags=["lists"])


@router.post("/", response_model=schemas.List)
async def create_list(list_data: schemas.ListCreate, db: AsyncSession = Depends(get_db)):
    """Create a new list"""
    # Verify project exists
    result = await db.execute(select(models.Project).filter(models.Project.id == list_data.project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get the maximum position for lists in this project
    count_result = await db.execute(
        select(func.count(models.List.id)).filter(models.List.project_id == list_data.project_id)
    )
    max_position = count_result.scalar() or 0
    
    db_list = models.List(
        name=list_data.name,
        project_id=list_data.project_id,
        position=max_position
    )
    db.add(db_list)
    await db.commit()
    await db.refresh(db_list)
    return db_list


@router.get("/", response_model=TypingList[schemas.List])
async def get_lists(project_id: int = None, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Get all lists, optionally filtered by project"""
    query = select(models.List)
    if project_id:
        query = query.filter(models.List.project_id == project_id)
    query = query.order_by(models.List.position).offset(skip).limit(limit)
    
    result = await db.execute(query)
    lists = result.scalars().all()
    return lists


@router.get("/{list_id}", response_model=schemas.List)
async def get_list(list_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific list"""
    result = await db.execute(select(models.List).filter(models.List.id == list_id))
    list_item = result.scalar_one_or_none()
    if not list_item:
        raise HTTPException(status_code=404, detail="List not found")
    return list_item


@router.put("/{list_id}", response_model=schemas.List)
async def rename_list(list_id: int, list_update: schemas.ListUpdate, db: AsyncSession = Depends(get_db)):
    """Rename a list"""
    result = await db.execute(select(models.List).filter(models.List.id == list_id))
    db_list = result.scalar_one_or_none()
    if not db_list:
        raise HTTPException(status_code=404, detail="List not found")
    
    db_list.name = list_update.name
    await db.commit()
    await db.refresh(db_list)
    return db_list


@router.delete("/{list_id}")
async def delete_list(list_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a list"""
    result = await db.execute(select(models.List).filter(models.List.id == list_id))
    db_list = result.scalar_one_or_none()
    if not db_list:
        raise HTTPException(status_code=404, detail="List not found")
    
    db.delete(db_list)
    await db.commit()
    return {"message": "List deleted successfully"}
