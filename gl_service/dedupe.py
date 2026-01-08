from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .models import Email


@dataclass(frozen=True)
class DedupeResult:
    kept: list[Email]
    dropped: list[Email]


def _ts(dt: datetime | None) -> float:
    if dt is None:
        return 0.0
    return dt.timestamp()


def dedupe_latest_per_thread(emails: list[Email]) -> DedupeResult:
    """
    Аналог ноды `dedupe-emails`:
    - ключ: threadId (если нет — id)
    - выбираем письмо с максимальным date
    """

    by_key: dict[str, tuple[float, int, Email]] = {}
    for i, email in enumerate(emails):
        key = email.thread_id or email.id or str(i)
        ts = _ts(email.date)
        prev = by_key.get(key)
        if prev is None or ts > prev[0]:
            by_key[key] = (ts, i, email)

    kept_items = list(by_key.values())  # (ts, i, email)
    kept_items.sort(key=lambda t: t[1])
    kept = [t[2] for t in kept_items]

    kept_set = set(id(e) for e in kept)
    dropped = [e for e in emails if id(e) not in kept_set]

    return DedupeResult(kept=kept, dropped=dropped)


