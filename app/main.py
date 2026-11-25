from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .routers import auth, board, chores, finance, parking, residents

settings = get_settings()

app = FastAPI(title=settings.app_name, version="1.0.0")

app.include_router(auth.router)
app.include_router(residents.router)
app.include_router(board.router)
app.include_router(chores.router)
app.include_router(finance.router)
app.include_router(parking.router)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok", "app": settings.app_name}


STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
