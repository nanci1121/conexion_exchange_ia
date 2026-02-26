import asyncio
import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .services.workflow_service import main_loop
from .api.routes import router
from .app_state import app_state

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EmailAI-API")

# =========== Lifespan ===========

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic"""
    logger.info("Starting background processing engine...")
    # Run main_loop in separate thread to avoid blocking FastAPI
    bg_task = asyncio.create_task(asyncio.to_thread(main_loop, app_state))
    
    yield
    
    logger.info("Shutting down background processing...")
    bg_task.cancel()

# =========== App Setup ===========

app = FastAPI(
    title="Email AI Dashboard",
    description="AI-powered email response system with Exchange integration",
    version="1.0.0",
    lifespan=lifespan
)

# Setup static files (handle both local dev and container paths)
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True, parents=True)

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    logger.info(f"Static files mounted from {static_dir}")
else:
    logger.warning(f"Static directory not found at {static_dir}")

# Include all routes
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
