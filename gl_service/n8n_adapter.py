from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from .models import Attachment, Email


_SIZE_RE = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*([a-zA-Z]{0,3})\s*$")


def _coerce_file_size(value: Any) -> int | None:
    """
    n8n binary.attachment_0.fileSize может быть:
    - int (bytes)
    - str вида '121 kB', '2.3 MB', '1024'
    Возвращаем bytes (int) или None.
    """

    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # pure int as string
        if s.isdigit():
            try:
                return int(s)
            except Exception:
                return None
        m = _SIZE_RE.match(s)
        if not m:
            return None
        num_s, unit = m.group(1), (m.group(2) or "B").lower()
        num = float(num_s.replace(",", "."))
        # SI units (kB/MB/GB) are common in UI. Accept KiB/MiB too.
        mul = {
            "b": 1,
            "kb": 1000,
            "mb": 1000**2,
            "gb": 1000**3,
            "kib": 1024,
            "mib": 1024**2,
            "gib": 1024**3,
        }.get(unit, 1)
        return int(num * mul)
    return None


def _coerce_email_field(value: Any) -> str:
    """
    n8n Gmail может отдавать from/to как строку или как объект:
    {
      "value": [{"address": "...", "name": "..."}],
      "text": "Name <email@example.com>"
    }
    """

    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        text = value.get("text")
        if isinstance(text, str) and text.strip():
            return text
        vals = value.get("value")
        if isinstance(vals, list) and vals:
            parts: list[str] = []
            for v in vals:
                if isinstance(v, str) and v.strip():
                    parts.append(v.strip())
                    continue
                if isinstance(v, dict):
                    addr = v.get("address") or ""
                    name = v.get("name") or ""
                    if addr and name:
                        parts.append(f'{name} <{addr}>')
                    elif addr:
                        parts.append(str(addr))
            return ", ".join([p for p in parts if p])
    # fallback: best-effort stringification
    try:
        return str(value)
    except Exception:
        return ""


def email_from_n8n_item(item: dict) -> Email:
    """
    Конвертер из формата n8n item -> Email.

    Ожидаем структуру:
    {
      "json": { id, threadId, subject, from, to, date, snippet, labelIds, ... },
      "binary": { "attachment_0": { data, fileName, mimeType, fileSize, fileExtension, ... } }
    }
    """

    js = item.get("json") or {}
    bn = item.get("binary") or {}

    date_val = js.get("date")
    dt: datetime | None = None
    if isinstance(date_val, str) and date_val:
        # Gmail node часто отдаёт ISO
        try:
            dt = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
        except Exception:
            dt = None

    att = None
    a0 = bn.get("attachment_0")
    if isinstance(a0, dict) and a0.get("data"):
        att = Attachment(
            file_name=a0.get("fileName") or "attachment",
            mime_type=a0.get("mimeType") or "application/octet-stream",
            file_size=_coerce_file_size(a0.get("fileSize")),
            file_extension=a0.get("fileExtension"),
            data_base64=a0.get("data"),
        )

    return Email(
        id=str(js.get("id") or ""),
        thread_id=js.get("threadId"),
        subject=js.get("subject") or "",
        **{"from": _coerce_email_field(js.get("from"))},  # alias
        to=_coerce_email_field(js.get("to")),
        date=dt,
        snippet=js.get("snippet") or "",
        label_ids=js.get("labelIds"),
        attachment=att,
    )


def email_to_n8n_item(email: Email) -> dict:
    """
    Обратный конвертер (Email -> n8n item), если хочешь хранить шаги в n8n item-структуре.
    """

    out = {
        "json": {
            "id": email.id,
            "threadId": email.thread_id,
            "subject": email.subject,
            "from": email.from_,
            "to": email.to,
            "date": email.date.isoformat() if email.date else None,
            "snippet": email.snippet,
            "labelIds": email.label_ids,
        },
        "binary": {},
    }

    if email.attachment is not None:
        out["binary"]["attachment_0"] = {
            "data": email.attachment.data_base64,
            "fileName": email.attachment.file_name,
            "mimeType": email.attachment.mime_type,
            "fileSize": email.attachment.file_size,
            "fileExtension": email.attachment.file_extension,
        }

    return out


