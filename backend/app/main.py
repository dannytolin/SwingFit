from fastapi import FastAPI

from backend.app.config import settings

app = FastAPI(title=settings.app_name)


@app.get("/")
def health_check():
    return {"status": "ok", "app": settings.app_name}
