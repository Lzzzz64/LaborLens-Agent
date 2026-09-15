from pathlib import Path

import pytest

from app.services.documents import DocumentParser, ParsedDocument, TextSpan, cleanup_orphans


class FakeReader:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def extract(self, path):
        self.calls += 1
        return self.result


class FakeOCR:
    def __init__(self):
        self.calls = []

    def read_pdf(self, path):
        self.calls.append("pdf")
        return ParsedDocument(text="合同签订日期 2026-09-13", page_count=1,
                              spans=[TextSpan(text="合同签订日期 2026-09-13", page=1, confidence=0.72)])

    def read_image(self, path):
        self.calls.append("image")
        return ParsedDocument(text="工资 5000 元，不得拖欠", page_count=1,
                              spans=[TextSpan(text="工资 5000 元，不得拖欠", page=1, confidence=0.81)])


def test_text_pdf_uses_reader_without_ocr(tmp_path):
    path = tmp_path / "contract.pdf"
    path.write_bytes(b"%PDF")
    reader = FakeReader(ParsedDocument(text="劳动合同条款 " * 8, page_count=1,
                                       spans=[TextSpan(text="劳动合同条款 " * 8, page=1, confidence=1)]))
    ocr = FakeOCR()
    result = DocumentParser(pdf_reader=reader, ocr=ocr).parse(path)
    assert result.text.startswith("劳动合同")
    assert not ocr.calls


def test_scanned_pdf_falls_back_to_ocr_and_marks_date(tmp_path):
    path = tmp_path / "scan.pdf"
    path.write_bytes(b"%PDF")
    parser = DocumentParser(pdf_reader=FakeReader(ParsedDocument(text="", page_count=1, spans=[])), ocr=FakeOCR())
    result = parser.parse(path)
    assert parser.ocr.calls == ["pdf"]
    assert any(span.critical_kind == "date" and span.confidence == 0.72 for span in result.spans)


def test_image_marks_amount_and_negation(tmp_path):
    path = tmp_path / "contract.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
    result = DocumentParser(pdf_reader=FakeReader(None), ocr=FakeOCR()).parse(path)
    assert {span.critical_kind for span in result.spans} >= {"amount", "negation"}


def test_old_orphans_are_removed_but_recent_files_remain(tmp_path):
    old = tmp_path / "upload-old.pdf"
    new = tmp_path / "upload-new.pdf"
    old.write_text("old")
    new.write_text("new")
    import os
    os.utime(old, (100, 100))
    cleanup_orphans(tmp_path, ttl_minutes=30, now=3600)
    assert not old.exists()
    assert new.exists()


def test_fixture_text_pdf_extracts_real_page_text():
    path = Path(__file__).parents[1] / "fixtures" / "text-contract.pdf"
    result = DocumentParser(ocr=FakeOCR()).parse(path)
    assert result.page_count == 1
    assert "Employment contract" in result.text
    assert any(span.critical_kind == "date" for span in result.spans)


def test_fixture_scanned_pdf_uses_ocr_fallback():
    path = Path(__file__).parents[1] / "fixtures" / "scanned-contract.pdf"
    ocr = FakeOCR()
    result = DocumentParser(ocr=ocr).parse(path)
    assert result.page_count == 1
    assert ocr.calls == ["pdf"]
