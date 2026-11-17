import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routers import public, admin, media
from app.templates import templates

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and seed sample luxury fleet on startup
    init_db()
    yield

app = FastAPI(
    title="MOTORA Luxury Automotive Marketplace",
    description="Exclusive online showroom for importing and selling world-class used vehicles to Egypt.",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static folder
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include routers
app.include_router(public.router)
app.include_router(admin.router)
app.include_router(media.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
