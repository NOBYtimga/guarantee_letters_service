from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Настройки берём из env — удобно для Cloud Run / GitHub Actions.
    Ничего секретного в репозиторий не кладём.
    """

    model_config = SettingsConfigDict(env_prefix="GL_", extra="ignore")

    # OpenAI
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    # Google Gemini (Generative Language API)
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"

    # Whapi (WhatsApp gateway)
    whapi_token: str | None = None
    whapi_base_url: str = "https://gate.whapi.cloud"
    whapi_to: str | None = None  # например: "120363178668706613@g.us"

    # Простая защита HTTP эндпоинтов (для Railway + n8n cloud).
    # Если задано — все POST эндпоинты (кроме /health) требуют заголовок `X-API-Key`.
    api_key: str | None = None


settings = Settings()


