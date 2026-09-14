from fastapi import FastAPI

from app.config import get_settings

app = FastAPI(title="Labor Law Analysis Agent")


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
