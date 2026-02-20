from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List as TypingList
from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=schemas.Task)
async def create_task(task: schemas.TaskCreate, db: AsyncSession = Depends(get_db)):
    """Create a new task"""
    # Verify list exists
    result = await db.execute(select(models.List).filter(models.List.id == task.list_id))
    list_item = result.scalar_one_or_none()
    if not list_item:
        raise HTTPException(status_code=404, detail="List not found")
    
    # Get the maximum position for tasks in this list
    count_result = await db.execute(
        select(func.count(models.Task.id)).filter(models.Task.list_id == task.list_id)
    )
    max_position = count_result.scalar() or 0
    
    db_task = models.Task(
        title=task.title,
        description=task.description,
        list_id=task.list_id,
        position=max_position
    )
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task


@router.get("/", response_model=TypingList[schemas.Task])
async def get_tasks(list_id: int = None, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Get all tasks, optionally filtered by list"""
    query = select(models.Task)
    if list_id:
        query = query.filter(models.Task.list_id == list_id)
    query = query.order_by(models.Task.position).offset(skip).limit(limit)
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    return tasks


@router.get("/{task_id}", response_model=schemas.Task)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific task"""
    result = await db.execute(select(models.Task).filter(models.Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=schemas.Task)
async def update_task(task_id: int, task_update: schemas.TaskUpdate, db: AsyncSession = Depends(get_db)):
    """Update a task"""
    result = await db.execute(select(models.Task).filter(models.Task.id == task_id))
    db_task = result.scalar_one_or_none()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task_update.title is not None:
        db_task.title = task_update.title
    if task_update.description is not None:
        db_task.description = task_update.description
    
    await db.commit()
    await db.refresh(db_task)
    return db_task


@router.delete("/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a task"""
    result = await db.execute(select(models.Task).filter(models.Task.id == task_id))
    db_task = result.scalar_one_or_none()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    list_id = db_task.list_id
    position = db_task.position
    
    db.delete(db_task)
    
    # Reorder remaining tasks in the list
    result = await db.execute(
        select(models.Task).filter(
            models.Task.list_id == list_id,
            models.Task.position > position
        )
    )
    remaining_tasks = result.scalars().all()
    
    for task in remaining_tasks:
        task.position -= 1
    
    await db.commit()
    return {"message": "Task deleted successfully"}


@router.post("/{task_id}/move", response_model=schemas.Task)
async def move_task(task_id: int, task_move: schemas.TaskMove, db: AsyncSession = Depends(get_db)):
    """Move a task to a different list and/or position"""
    result = await db.execute(select(models.Task).filter(models.Task.id == task_id))
    db_task = result.scalar_one_or_none()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Verify target list exists
    list_result = await db.execute(select(models.List).filter(models.List.id == task_move.list_id))
    target_list = list_result.scalar_one_or_none()
    if not target_list:
        raise HTTPException(status_code=404, detail="Target list not found")
    
    old_list_id = db_task.list_id
    old_position = db_task.position
    new_list_id = task_move.list_id
    new_position = task_move.position
    
    # Get max position in target list
    count_result = await db.execute(
        select(func.count(models.Task.id)).filter(models.Task.list_id == new_list_id)
    )
    max_position = count_result.scalar() or 0
    
    # Validate new position
    if new_position < 0 or new_position > max_position:
        raise HTTPException(status_code=400, detail=f"Position must be between 0 and {max_position}")
    
    # If moving within the same list
    if old_list_id == new_list_id:
        if old_position == new_position:
            # No change needed
            return db_task
        
        # Moving within same list
        if old_position < new_position:
            # Moving down: shift tasks up
            result = await db.execute(
                select(models.Task).filter(
                    models.Task.list_id == old_list_id,
                    models.Task.position > old_position,
                    models.Task.position <= new_position,
                    models.Task.id != task_id
                )
            )
            tasks_to_shift = result.scalars().all()
            for task in tasks_to_shift:
                task.position -= 1
        else:
            # Moving up: shift tasks down
            result = await db.execute(
                select(models.Task).filter(
                    models.Task.list_id == old_list_id,
                    models.Task.position >= new_position,
                    models.Task.position < old_position,
                    models.Task.id != task_id
                )
            )
            tasks_to_shift = result.scalars().all()
            for task in tasks_to_shift:
                task.position += 1
    else:
        # Moving to different list
        # Shift tasks in old list up
        result = await db.execute(
            select(models.Task).filter(
                models.Task.list_id == old_list_id,
                models.Task.position > old_position,
                models.Task.id != task_id
            )
        )
        tasks_in_old_list = result.scalars().all()
        for task in tasks_in_old_list:
            task.position -= 1
        
        # Shift tasks in new list down
        result = await db.execute(
            select(models.Task).filter(
                models.Task.list_id == new_list_id,
                models.Task.position >= new_position,
                models.Task.id != task_id
            )
        )
        tasks_in_new_list = result.scalars().all()
        for task in tasks_in_new_list:
            task.position += 1
    
    # Update task
    db_task.list_id = new_list_id
    db_task.position = new_position
    
    await db.commit()
    await db.refresh(db_task)
    return db_task


@router.post("/{task_id}/reposition", response_model=schemas.Task)
async def reposition_task(task_id: int, reposition: schemas.TaskReposition, db: AsyncSession = Depends(get_db)):
    """Reposition a task within its current list"""
    result = await db.execute(select(models.Task).filter(models.Task.id == task_id))
    db_task = result.scalar_one_or_none()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    list_id = db_task.list_id
    old_position = db_task.position
    new_position = reposition.position
    
    # Get max position in the list
    count_result = await db.execute(
        select(func.count(models.Task.id)).filter(models.Task.list_id == list_id)
    )
    max_position = (count_result.scalar() or 1) - 1  # -1 because we're excluding the current task
    
    # Validate new position
    if new_position < 0 or new_position > max_position:
        raise HTTPException(status_code=400, detail=f"Position must be between 0 and {max_position}")
    
    if old_position == new_position:
        # No change needed
        return db_task
    
    # Reposition within same list
    if old_position < new_position:
        # Moving down: shift tasks up
        result = await db.execute(
            select(models.Task).filter(
                models.Task.list_id == list_id,
                models.Task.position > old_position,
                models.Task.position <= new_position,
                models.Task.id != task_id
            )
        )
        tasks_to_shift = result.scalars().all()
        for task in tasks_to_shift:
            task.position -= 1
    else:
        # Moving up: shift tasks down
        result = await db.execute(
            select(models.Task).filter(
                models.Task.list_id == list_id,
                models.Task.position >= new_position,
                models.Task.position < old_position,
                models.Task.id != task_id
            )
        )
        tasks_to_shift = result.scalars().all()
        for task in tasks_to_shift:
            task.position += 1
    
    db_task.position = new_position
    await db.commit()
    await db.refresh(db_task)
    return db_task
