import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path


class UnsupportedDocumentError(ValueError):
    pass


@dataclass
class TextSpan:
    text: str
    page: int
    confidence: float
    critical_kind: str | None = None


@dataclass
class ParsedDocument:
    text: str
    page_count: int
    spans: list[TextSpan]
    warnings: list[str] = field(default_factory=list)


class PDFReader:
    def extract(self, path: Path) -> ParsedDocument:
        import fitz
        with fitz.open(path) as document:
            spans = [TextSpan(text=line.strip(), page=page.number + 1, confidence=1.0)
                     for page in document for line in page.get_text().splitlines() if line.strip()]
            return ParsedDocument(text="\n".join(span.text for span in spans),
                                  page_count=len(document), spans=spans)


class TesseractOCR:
    def _read(self, image, page: int) -> list[TextSpan]:
        import pytesseract
        from pytesseract import Output
        data = pytesseract.image_to_data(image, lang="chi_sim+eng", output_type=Output.DICT)
        return [TextSpan(text=word.strip(), page=page, confidence=max(0, min(1, float(conf) / 100)))
                for word, conf in zip(data["text"], data["conf"])
                if word.strip() and float(conf) >= 0]

    def read_pdf(self, path: Path) -> ParsedDocument:
        import fitz
        from PIL import Image
        spans = []
        with fitz.open(path) as document:
            for page in document:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                spans.extend(self._read(image, page.number + 1))
            count = len(document)
        return ParsedDocument(text=" ".join(s.text for s in spans), page_count=count, spans=spans,
                              warnings=[] if spans else ["OCR 未识别到文字"])

    def read_image(self, path: Path) -> ParsedDocument:
        from PIL import Image
        with Image.open(path) as image:
            spans = self._read(image, 1)
        return ParsedDocument(text=" ".join(s.text for s in spans), page_count=1, spans=spans,
                              warnings=[] if spans else ["OCR 未识别到文字"])


CRITICAL = {
    "date": re.compile(r"(?:19|20)\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}日?"),
    "amount": re.compile(r"(?:[¥￥]\s*)?\d+(?:\.\d+)?\s*(?:元|万元|人民币)"),
    "negation": re.compile(r"不得|不予|未|没有|禁止|无"),
}


def mark_critical_spans(result: ParsedDocument) -> ParsedDocument:
    marked = []
    for span in result.spans:
        marked.append(span)
        for kind, pattern in CRITICAL.items():
            marked.extend(TextSpan(text=match.group(), page=span.page, confidence=span.confidence,
                                   critical_kind=kind) for match in pattern.finditer(span.text))
    result.spans = marked
    return result


class DocumentParser:
    def __init__(self, pdf_reader=None, ocr=None):
        self.pdf_reader = pdf_reader or PDFReader()
        self.ocr = ocr or TesseractOCR()

    def parse(self, path: Path) -> ParsedDocument:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            result = self.pdf_reader.extract(path)
            if len(re.sub(r"\s", "", result.text)) < 40:
                result = self.ocr.read_pdf(path)
        elif suffix in {".png", ".jpg", ".jpeg", ".webp"}:
            result = self.ocr.read_image(path)
        else:
            raise UnsupportedDocumentError(suffix)
        return mark_critical_spans(result)


def cleanup_orphans(directory: Path, ttl_minutes: int, now: float | None = None) -> None:
    if not directory.exists():
        return
    cutoff = (time.time() if now is None else now) - ttl_minutes * 60
    for path in directory.glob("upload-*"):
        if path.is_file() and path.stat().st_mtime < cutoff:
            path.unlink(missing_ok=True)
