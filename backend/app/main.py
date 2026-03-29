from fastapi import FastAPI

from backend.app.config import settings
from backend.app.routers.clubs import router as clubs_router
from backend.app.routers.fitting import router as fitting_router
from backend.app.routers.ingest import router as ingest_router
from backend.app.routers.sessions import router as sessions_router

app = FastAPI(title=settings.app_name)
app.include_router(clubs_router)
app.include_router(sessions_router)
app.include_router(ingest_router)
app.include_router(fitting_router)


@app.get("/")
def health_check():
    return {"status": "ok", "app": settings.app_name}
