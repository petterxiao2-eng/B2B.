"""Main FastAPI application entry point."""
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager

from app.database import init_db
from app.api.projects import router as projects_router
from app.api.companies import router as companies_router
from app.api.contacts import router as contacts_router
from app.api.search import router as search_router
from app.api.drafts import router as drafts_router
from app.api.dashboard import router as dashboard_router

# Frontend static files directory
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database
    await init_db()
    yield
    # Shutdown: cleanup


app = FastAPI(
    title="B2B Customer Growth System",
    description="Automated cross-border B2B customer discovery, scoring, and outreach platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(dashboard_router)
app.include_router(projects_router)
app.include_router(companies_router)
app.include_router(contacts_router)
app.include_router(search_router)
app.include_router(drafts_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# Serve frontend static files (production mode)
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(request: Request, full_path: str = ""):
        # Try to serve the exact file first
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        # Fall back to index.html for SPA routing
        index_path = FRONTEND_DIST / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return JSONResponse({"service": "B2B Customer Growth System", "version": "1.0.0", "status": "running", "docs": "/docs"})
else:
    @app.get("/")
    async def root():
        return {
            "service": "B2B Customer Growth System",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs"
        }
