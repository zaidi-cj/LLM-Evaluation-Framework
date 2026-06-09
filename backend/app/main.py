from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.core.config import settings
from app.core.database import engine, Base
# Import models to ensure they are registered with Base metadata
from app.models.models import Project, TestCase, ModelConfiguration, EvaluationRun, EvaluationResult
from app.api import projects, testcases, runs

# Create database tables automatically for ease of local development
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="API server for LLM benchmark execution and regression analysis dashboard.",
    version="1.0.0"
)

# Enable CORS for Next.js communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(projects.router)
# Test cases are nested under projects for creation but we include them in the router path
app.include_router(testcases.router)
app.include_router(runs.router)

# Mount static dashboard folder if it exists
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/dashboard")
def read_dashboard():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "database": settings.DATABASE_URL.split("://")[0],
        "dashboard_url": "/dashboard"
    }
