from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.routers.affiliate import router as affiliate_router
from backend.app.routers.clubs import router as clubs_router
from backend.app.routers.fitting import router as fitting_router
from backend.app.routers.ingest import router as ingest_router
from backend.app.routers.sessions import router as sessions_router

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(clubs_router)
app.include_router(sessions_router)
app.include_router(ingest_router)
app.include_router(fitting_router)
app.include_router(affiliate_router)


@app.get("/")
def health_check():
    return {"status": "ok", "app": settings.app_name}
