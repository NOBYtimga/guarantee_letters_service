from __future__ import annotations

from datetime import datetime

from .models import Attachment, Email


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
            file_size=a0.get("fileSize"),
            file_extension=a0.get("fileExtension"),
            data_base64=a0.get("data"),
        )

    return Email(
        id=str(js.get("id") or ""),
        thread_id=js.get("threadId"),
        subject=js.get("subject") or "",
        **{"from": js.get("from") or ""},  # alias
        to=js.get("to"),
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


