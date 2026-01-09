from __future__ import annotations

import base64
import io
from dataclasses import dataclass

from pdfminer.high_level import extract_text as pdf_extract_text
from striprtf.striprtf import rtf_to_text

from .models import Attachment, ExtractMode


@dataclass(frozen=True)
class Extracted:
    mode: ExtractMode
    text: str | None
    mime_type: str
    raw_bytes: bytes


def _decode_base64(data_base64: str) -> bytes:
    return base64.b64decode(data_base64, validate=False)


def guess_mode(att: Attachment) -> ExtractMode:
    ext = (att.file_extension or "").lower().lstrip(".")
    if ext == "pdf" or att.mime_type == "application/pdf":
        return "pdf"
    if ext == "rtf" or att.mime_type in {"application/rtf", "text/rtf"}:
        return "rtf"
    return "other"


def extract_from_attachment(att: Attachment) -> Extracted:
    raw = _decode_base64(att.data_base64)
    mode = guess_mode(att)
    
    # Диагностика
    print(f"📦 File: {att.file_name}")
    print(f"📦 Size after decode: {len(raw)} bytes")
    print(f"📦 First 30 bytes: {raw[:30]}")
    print(f"📦 Mode: {mode}")

    if mode == "pdf":
        try:
            text = pdf_extract_text(io.BytesIO(raw)) or ""
            print(f"📦 PDF text extracted: {len(text)} chars")
            if not text.strip():
                print("⚠️ PDF parsed but text is empty!")
            return Extracted(mode=mode, text=text.strip(), mime_type=att.mime_type, raw_bytes=raw)
        except Exception as e:
            # PDF поврежден или это не PDF — отправляем как inline_data в Gemini
            print(f"❌ PDF extraction failed: {e}")
            return Extracted(mode="other", text=None, mime_type=att.mime_type, raw_bytes=raw)

    if mode == "rtf":
        try:
            # RTF часто в cp1251/ansi; striprtf работает по строке — декодируем максимально мягко
            decoded = raw.decode("utf-8", errors="ignore")
            if not decoded.strip():
                decoded = raw.decode("cp1251", errors="ignore")
            text = rtf_to_text(decoded) or ""
            return Extracted(mode=mode, text=text.strip(), mime_type=att.mime_type, raw_bytes=raw)
        except Exception:
            # RTF поврежден — отправляем как inline_data в Gemini
            return Extracted(mode="other", text=None, mime_type=att.mime_type, raw_bytes=raw)

    # other: текст не извлекаем, остаётся base64/inline_data для Gemini
    return Extracted(mode=mode, text=None, mime_type=att.mime_type, raw_bytes=raw)


