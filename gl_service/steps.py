from __future__ import annotations

from .dedupe import dedupe_latest_per_thread
from .extract import extract_from_attachment
from .gemini_client import analyze_document_with_gemini
from .gemini_parse import parse_gemini_json_text
from .message import build_whatsapp_message
from .models import Attachment, ClassifyResult, Email, GuaranteeDocExtract
from .openai_client import classify_is_guarantee_letter


def step_dedupe_latest(emails: list[Email]) -> tuple[list[Email], int]:
    """
    Шаг 1 (аналог `dedupe-emails`): оставляем последнее письмо на threadId.
    Возвращает (kept, dropped_count)
    """

    res = dedupe_latest_per_thread(emails)
    return res.kept, len(res.dropped)


async def step_classify(email: Email) -> ClassifyResult:
    """
    Шаг 2 (аналог `OpenAI Classify` + parser): is_guarantee_letter.
    """

    return await classify_is_guarantee_letter(subject=email.subject, from_=email.from_, snippet=email.snippet)


async def step_analyze_attachment(email: Email) -> tuple[GuaranteeDocExtract | None, Attachment | None]:
    """
    Шаг 3 (аналог `Проверка формата файла` + `Extract...` + `Gemini...` + `Парсинг Gemini`)
    """

    if email.attachment is None:
        return None, None

    try:
        extracted = extract_from_attachment(email.attachment)
        ai = await analyze_document_with_gemini(
            doc_text=extracted.text,
            file_bytes=None if extracted.text is not None else extracted.raw_bytes,
            mime_type=extracted.mime_type,
            subject=email.subject,
            snippet=email.snippet,
            parser=parse_gemini_json_text,
        )
        return ai, email.attachment
    except Exception as e:
        # Если вложение не удалось обработать (поврежден, пуст и т.д.)
        return GuaranteeDocExtract(
            summary=f"⚠️ Не удалось обработать вложение '{email.attachment.file_name}': {str(e)}"
        ), email.attachment


def step_no_attachment_fallback(email: Email) -> GuaranteeDocExtract:
    """
    Шаг 3b (аналог `Без вложения`)
    """

    return GuaranteeDocExtract(summary=f"Гарантийное письмо без вложения. Тема: {email.subject}")


def step_build_message(ai: GuaranteeDocExtract | None) -> str:
    """
    Шаг 4 (аналог `Подготовка сообщения`)
    """

    return build_whatsapp_message(ai)


