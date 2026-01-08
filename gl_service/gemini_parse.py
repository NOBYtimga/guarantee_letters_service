from __future__ import annotations

import json
import re

from .models import GuaranteeDocExtract


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def parse_gemini_json_text(raw_text: str | None) -> GuaranteeDocExtract:
    """
    Аналог логики `Парсинг Gemini` в n8n:
    - убираем ```json fences
    - пытаемся JSON.parse
    - если не получилось — кладём весь текст в summary
    """

    text = (raw_text or "{}").strip()
    text = _FENCE_RE.sub("", text).strip()

    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return GuaranteeDocExtract.model_validate(obj)
    except Exception:
        pass

    return GuaranteeDocExtract(summary=text or "Не удалось распознать")


