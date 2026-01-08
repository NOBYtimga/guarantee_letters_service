from __future__ import annotations

import base64

import httpx

from .models import GuaranteeDocExtract
from .settings import settings


class GeminiError(RuntimeError):
    pass


def _prompt_for_text(doc_text: str, subject: str, snippet: str) -> str:
    # По смыслу повторяет ваши промпты в n8n: "верни только JSON без markdown"
    return (
        "Проанализируй документ - гарантийное письмо от страховой.\n\n"
        f"Текст документа:\n{doc_text}\n\n"
        "Извлеки и верни ТОЛЬКО JSON (без markdown, без ```json):\n"
        '{"insurance_company": "название страховой", "patient_name": "ФИО пациента", '
        '"policy_number": "номер полиса", "services": "услуги/лимит", '
        '"valid_until": "срок действия", "summary": "резюме 2-3 предложения"}\n\n'
        f'Письмо: {subject} - {snippet}'
    )


def _prompt_for_inline(subject: str, snippet: str) -> str:
    return (
        "Проанализируй документ - гарантийное письмо от страховой.\n\n"
        "Извлеки и верни ТОЛЬКО JSON (без markdown, без ```json):\n"
        '{"insurance_company": "название страховой", "patient_name": "ФИО пациента", '
        '"policy_number": "номер полиса", "services": "услуги/лимит", '
        '"valid_until": "срок действия", "summary": "резюме 2-3 предложения"}\n\n'
        f'Письмо: {subject} - {snippet}'
    )


async def gemini_generate_from_text(doc_text: str, *, subject: str = "", snippet: str = "") -> str:
    if not settings.gemini_api_key:
        raise GeminiError("GL_GEMINI_API_KEY is not set")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"

    payload = {
        "contents": [{"parts": [{"text": _prompt_for_text(doc_text, subject, snippet)}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1000},
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, params={"key": settings.gemini_api_key}, json=payload)
        if resp.status_code >= 400:
            raise GeminiError(f"Gemini HTTP {resp.status_code}: {resp.text}")
        data = resp.json()

    return (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "")
    )


async def gemini_generate_from_inline_file(
    file_bytes: bytes,
    *,
    mime_type: str,
    subject: str = "",
    snippet: str = "",
) -> str:
    if not settings.gemini_api_key:
        raise GeminiError("GL_GEMINI_API_KEY is not set")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": _prompt_for_inline(subject, snippet)},
                    {
                        "inline_data": {
                            "mime_type": mime_type or "application/octet-stream",
                            "data": base64.b64encode(file_bytes).decode("ascii"),
                        }
                    },
                ]
            }
        ],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1000},
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, params={"key": settings.gemini_api_key}, json=payload)
        if resp.status_code >= 400:
            raise GeminiError(f"Gemini HTTP {resp.status_code}: {resp.text}")
        data = resp.json()

    return (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "")
    )


async def analyze_document_with_gemini(
    *,
    doc_text: str | None,
    file_bytes: bytes | None,
    mime_type: str,
    subject: str,
    snippet: str,
    parser,
) -> GuaranteeDocExtract:
    """
    Единая точка как в n8n:
    - PDF/RTF -> doc_text
    - other -> inline_data (file_bytes + mime_type)
    """

    if doc_text is not None:
        raw = await gemini_generate_from_text(doc_text, subject=subject, snippet=snippet)
        return parser(raw)

    if file_bytes is not None:
        raw = await gemini_generate_from_inline_file(
            file_bytes, mime_type=mime_type, subject=subject, snippet=snippet
        )
        return parser(raw)

    raise GeminiError("No doc_text or file_bytes provided")


