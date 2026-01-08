from __future__ import annotations

import base64

import httpx

from .models import Attachment, WhatsAppSendResult
from .settings import settings


class WhapiError(RuntimeError):
    pass


def _auth_headers() -> dict[str, str]:
    if not settings.whapi_token:
        raise WhapiError("GL_WHAPI_TOKEN is not set")
    return {"Authorization": f"Bearer {settings.whapi_token}"}


async def send_text(*, to: str, body: str) -> str | None:
    url = f"{settings.whapi_base_url.rstrip('/')}/messages/text"
    payload = {"to": to, "body": body}
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json=payload, headers=_auth_headers())
        if resp.status_code >= 400:
            raise WhapiError(f"Whapi HTTP {resp.status_code}: {resp.text}")
        data = resp.json()
    # В разных версиях API поле id может называться по-разному — оставляем best-effort
    return data.get("id") or data.get("message", {}).get("id")


async def send_document(*, to: str, caption: str, attachment: Attachment) -> str | None:
    url = f"{settings.whapi_base_url.rstrip('/')}/messages/document"

    raw = base64.b64decode(attachment.data_base64, validate=False)
    files = {
        "media": (attachment.file_name, raw, attachment.mime_type or "application/octet-stream"),
    }
    data = {
        "to": to,
        "caption": caption,
    }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, data=data, files=files, headers=_auth_headers())
        if resp.status_code >= 400:
            raise WhapiError(f"Whapi HTTP {resp.status_code}: {resp.text}")
        js = resp.json()

    return js.get("id") or js.get("message", {}).get("id")


async def send_text_and_optional_doc(
    *,
    to: str,
    text: str,
    attachment: Attachment | None,
) -> WhatsAppSendResult:
    text_id = await send_text(to=to, body=text)
    doc_id = None
    if attachment is not None:
        doc_id = await send_document(to=to, caption=f"📎 {attachment.file_name}", attachment=attachment)
    return WhatsAppSendResult(ok=True, text_message_id=text_id, document_message_id=doc_id)


