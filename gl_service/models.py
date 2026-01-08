from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Attachment(BaseModel):
    """
    Унифицированный формат вложения (аналогично n8n binary.attachment_0).

    data_base64 — содержимое файла в base64 (без data: prefix)
    """

    file_name: str
    mime_type: str = "application/octet-stream"
    file_size: int | None = None
    file_extension: str | None = None
    data_base64: str


class Email(BaseModel):
    id: str
    thread_id: str | None = None
    subject: str = ""
    from_: str = Field(default="", alias="from")
    to: str | None = None
    date: datetime | None = None
    snippet: str = ""
    label_ids: list[str] | None = None
    attachment: Attachment | None = None


class ClassifyResult(BaseModel):
    is_guarantee_letter: bool


class GuaranteeDocExtract(BaseModel):
    insurance_company: str = ""
    patient_name: str = ""
    policy_number: str = ""
    services: str = ""
    valid_until: str = ""
    summary: str = ""

class WhatsAppSendResult(BaseModel):
    ok: bool
    text_message_id: str | None = None
    document_message_id: str | None = None
    raw: Any | None = None


ExtractMode = Literal["pdf", "rtf", "other"]


