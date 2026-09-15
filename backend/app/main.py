import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.config import get_settings
from app.api.cases import router as cases_router
from app.api.cases import UPLOAD_DIR
from app.services.documents import cleanup_orphans


@asynccontextmanager
async def lifespan(app: FastAPI):
    async def janitor():
        while True:
            cleanup_orphans(UPLOAD_DIR, get_settings().upload_ttl_minutes)
            await asyncio.sleep(60)
    task = asyncio.create_task(janitor())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

app = FastAPI(title="Labor Law Analysis Agent", lifespan=lifespan)
app.include_router(cases_router)


def check_mysql() -> bool:
    get_settings()
    return True


def check_chroma() -> bool:
    get_settings()
    return True


@app.get("/health")
def health() -> dict[str, str]:
    mysql_ok = check_mysql()
    chroma_ok = check_chroma()
    return {
        "status": "ok" if mysql_ok and chroma_ok else "degraded",
        "mysql": "ok" if mysql_ok else "error",
        "chroma": "ok" if chroma_ok else "error",
    }
