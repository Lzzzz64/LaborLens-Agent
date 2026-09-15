import shutil
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.models import CaseModel
from app.db.repositories import CaseRepository
from app.domain.models import CaseKind, CaseRecord
from app.services.documents import DocumentParser, ParsedDocument, cleanup_orphans

router = APIRouter(prefix="/cases", tags=["cases"])
UPLOAD_DIR = Path(gettempdir()) / "labor-lens-uploads"
_session_factory = None


def get_session():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(create_engine(get_settings().database_url, pool_pre_ping=True))
    with _session_factory() as session:
        yield session


def get_parser() -> DocumentParser:
    return DocumentParser()


class CreateCase(BaseModel):
    kind: CaseKind
    goal: str = Field(min_length=1)


@router.post("", response_model=CaseRecord, status_code=201)
def create_case(request: CreateCase, session: Session = Depends(get_session)):
    return CaseRepository(session).create(request.kind, request.goal)


ALLOWED = {
    ".pdf": ("application/pdf", b"%PDF"),
    ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
    ".webp": ("image/webp", b"RIFF"),
}


@router.post("/{case_id}/documents", response_model=ParsedDocument)
def upload_document(case_id: str, file: UploadFile = File(...), session: Session = Depends(get_session),
                    parser: DocumentParser = Depends(get_parser)):
    case = session.get(CaseModel, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="案件不存在")
    suffix = Path(file.filename or "").suffix.lower()
    expected = ALLOWED.get(suffix)
    if not expected or file.content_type != expected[0]:
        raise HTTPException(status_code=415, detail="不支持的文件类型")
    header = file.file.read(max(12, len(expected[1])))
    file.file.seek(0)
    if not header.startswith(expected[1]) or (suffix == ".webp" and header[8:12] != b"WEBP"):
        raise HTTPException(status_code=415, detail="文件内容与类型不符")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    cleanup_orphans(UPLOAD_DIR, get_settings().upload_ttl_minutes)
    path = UPLOAD_DIR / f"upload-{uuid4()}{suffix}"
    case.status = "parsing"
    session.commit()
    try:
        with path.open("wb") as target:
            shutil.copyfileobj(file.file, target)
        last_error = None
        for _ in range(3):
            try:
                result = parser.parse(path)
                break
            except Exception as error:
                last_error = error
        else:
            raise last_error
        case.status = "created"
        case.analysis_state = {**(case.analysis_state or {}), "parsed_text": result.text,
                               "parse_warnings": result.warnings}
        session.commit()
        return result
    except Exception as error:
        session.rollback()
        case = session.get(CaseModel, case_id)
        case.status = "parse_failed"
        session.commit()
        raise HTTPException(status_code=503, detail={"code": "OCR_FAILED", "message": str(error)}) from error
    finally:
        file.file.close()
        path.unlink(missing_ok=True)
