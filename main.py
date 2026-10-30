import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.database import engine, Base, SessionLocal
from app.models import Task
from app.routers import tasks, upload, ai_agent, reports
from app.routers.tasks import seed_database

# Create SQLite tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="OpsPilot Pro",
    description="Operational workflow intelligence for SAP processes.",
    version="1.0.0"
)

# CORS Policy configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(tasks.router)
app.include_router(upload.router)
app.include_router(ai_agent.router)
app.include_router(reports.router)

# Mount static folder for frontend SPA assets
static_path = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_path):
    os.makedirs(static_path)
    os.makedirs(os.path.join(static_path, "css"))
    os.makedirs(os.path.join(static_path, "js"))

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_frontend():
    """Serves the single page dashboard frontend."""
    return FileResponse("static/index.html")

# Auto-seed on first start if db is empty
@app.on_event("startup")
def check_and_seed_db():
    db = SessionLocal()
    try:
        task_count = db.query(Task).count()
        if task_count == 0:
            print("Database is empty. Running auto-seeding...")
            seed_database(db)
    except Exception as e:
        print(f"Error checking/seeding database: {e}")
    finally:
        db.close()
