from __future__ import annotations

import httpx

from .models import ClassifyResult
from .settings import settings


class OpenAIError(RuntimeError):
    pass


_CLASSIFY_PROMPT = """\
Проанализируй письмо и определи, является ли оно гарантийным письмом от страховой компании.

Признаки гарантийного письма:
- Отправитель: страховая компания (АльфаСтрахование, СОГАЗ, Ингосстрах, ВСК, РЕСО и др.)
- Тема содержит: "гарантийное письмо", "гарантия", "ГП"
- В тексте есть: ФИО пациента, номер полиса, медицинские услуги

НЕ является гарантийным письмом: реклама, счета, акты, уведомления.

Данные письма:
Тема: {subject}
От: {from_}
Текст: {snippet}

Верни ТОЛЬКО JSON без markdown, строго формата: {{"is_guarantee_letter": true/false}}
"""


async def classify_is_guarantee_letter(*, subject: str, from_: str, snippet: str) -> ClassifyResult:
    """
    Упрощённый аналог вашего `OpenAI Classify` + structured parser.
    """

    if not settings.openai_api_key:
        raise OpenAIError("GL_OPENAI_API_KEY is not set")

    prompt = _CLASSIFY_PROMPT.format(subject=subject or "", from_=from_ or "", snippet=snippet or "")

    # Chat Completions — минимальная зависимость (без SDK).
    # Просим вернуть JSON object; дальше валидируем pydantic-моделью.
    payload = {
        "model": settings.openai_model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Ты аккуратный помощник. Возвращай только валидный JSON."},
            {"role": "user", "content": prompt},
        ],
    }

    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
        if resp.status_code >= 400:
            raise OpenAIError(f"OpenAI HTTP {resp.status_code}: {resp.text}")
        data = resp.json()

    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )

    try:
        # pydantic сам распарсит dict, но тут приходит строка
        return ClassifyResult.model_validate_json(content)
    except Exception as e:
        raise OpenAIError(f"Failed to parse OpenAI JSON: {content}") from e


