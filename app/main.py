from fastapi import FastAPI

from app.database import Base, engine
from app.routers import auth, backfill, stats

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Gatekeepify",
    description="Prove you listened first.",
    version="0.1.0",
)

app.include_router(auth.router)
app.include_router(stats.router)
app.include_router(backfill.router)


@app.get("/health")
def health():
    return {"status": "ok"}
