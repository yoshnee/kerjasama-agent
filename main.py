import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.webhook import router as webhook_router, init_services

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup
    logger.info("Starting up Kerjasama Agent...")
    init_services()
    logger.info("Startup complete")

    yield

    # Shutdown
    logger.info("Shutting down Kerjasama Agent...")


app = FastAPI(
    title="Kerjasama Agent",
    version="0.1.0",
    lifespan=lifespan
)

# Include webhook router
app.include_router(webhook_router)


@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
