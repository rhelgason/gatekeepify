import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.database import Base, engine
from app.routers import auth, backfill, friends, gatekeep, stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("gatekeepify.http")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Gatekeepify",
    description="Prove you listened first.",
    version="0.1.0",
)

app.include_router(auth.router)
app.include_router(stats.router)
app.include_router(backfill.router)
app.include_router(friends.router)
app.include_router(gatekeep.router)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
    except Exception:
        duration = time.time() - start
        logger.error(
            f"{request.method} {request.url.path} -> 500 ({duration:.3f}s)"
        )
        raise
    duration = time.time() - start
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({duration:.3f}s)"
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
def health():
    return {"status": "ok"}
