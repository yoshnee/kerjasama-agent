import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.routes.chat import router as chat_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Kerjasama Chat API", version="1.0.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://chat.kerjasama.dev",
        "http://localhost:8080",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(chat_router)


@app.get("/")
async def health():
    return {"status": "healthy"}
