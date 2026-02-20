from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


# Project Schemas
class ProjectBase(BaseModel):
    name: str


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str


class Project(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# List Schemas
class ListBase(BaseModel):
    name: str
    project_id: int


class ListCreate(ListBase):
    pass


class ListUpdate(BaseModel):
    name: str


class List(ListBase):
    id: int
    position: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Task Schemas
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    list_id: int


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class TaskMove(BaseModel):
    list_id: int
    position: int


class TaskReposition(BaseModel):
    position: int


class Task(TaskBase):
    id: int
    position: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
