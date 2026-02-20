from fastapi import FastAPI
from app.database import init_db
from app.routers import projects, lists, tasks

app = FastAPI(title="TaskFlow API", version="1.0.0")


@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup"""
    await init_db()


# Include routers
app.include_router(projects.router)
app.include_router(lists.router)
app.include_router(tasks.router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to TaskFlow API",
        "docs": "/docs",
        "version": "1.0.0"
    }
