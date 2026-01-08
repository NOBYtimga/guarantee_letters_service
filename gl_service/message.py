from __future__ import annotations

from .models import GuaranteeDocExtract


def build_whatsapp_message(ai: GuaranteeDocExtract | None) -> str:
    """
    Повторяет ваш шаблон `Подготовка сообщения` (без n8n-выражений).
    """

    insurance = (ai.insurance_company if ai else "") or "Не определена"
    patient = (ai.patient_name if ai else "") or "Не указан"
    policy = (ai.policy_number if ai else "") or "Не указан"
    services = (ai.services if ai else "") or "Не указаны"
    valid_until = (ai.valid_until if ai else "") or "Не указано"
    summary = (ai.summary if ai else "") or ""

    return (
        "📋 *ГАРАНТИЙНОЕ ПИСЬМО*\n\n"
        f"🏥 *Страховая:* {insurance}\n"
        f"👤 *Пациент:* {patient}\n"
        f"📄 *Полис:* {policy}\n"
        f"💊 *Услуги:* {services}\n"
        f"📅 *До:* {valid_until}\n\n"
        f"📝 {summary}"
    )


