# Guarantee Letters Service

Небольшой **HTTP‑сервис для n8n**, который выносит “сложные части” пайплайна обработки писем с гарантийными письмами в код:

- **dedupe писем** (оставляем последнее письмо в треде)
- **классификация** письма как “гарантийное/не гарантийное” через OpenAI
- **обработка вложений**: PDF/RTF → извлечение текста, прочие форматы → отправка файла в Gemini как `inline_data`
- **анализ документа** через Gemini и приведение ответа к JSON
- **формирование текста** сообщения для WhatsApp
- (опционально) **отправка в WhatsApp** через Whapi (текст + документ)

Идея: **n8n остаётся оркестратором** (Gmail, фильтры, ветвления, расписание), а сервис даёт стабильные “шаги-функции” по HTTP.

Вариант A: один небольшой HTTP-сервис (FastAPI) с набором “функций” (эндпоинтов), которые n8n cloud дергает по очереди.
- дедуп писем по `threadId` (берём последнее по `date`)
- OpenAI-классификация (гарантийное/не гарантийное)
- обработка вложений: PDF/RTF → текст, другие форматы → inline base64
- анализ документа через Gemini и парсинг результата в JSON
- (опционально) отправка в WhatsApp через Whapi (текст + документ)

## Переменные окружения

- `GL_OPENAI_API_KEY` — ключ OpenAI (классификация)
- `GL_OPENAI_MODEL` — по умолчанию `gpt-4o-mini`
- `GL_GEMINI_API_KEY` — ключ Gemini
- `GL_GEMINI_MODEL` — по умолчанию `gemini-2.0-flash`
- `GL_WHAPI_TOKEN` — токен Whapi
- `GL_WHAPI_TO` — получатель (например `120363178668706613@g.us`)
- `GL_WHAPI_BASE_URL` — по умолчанию `https://gate.whapi.cloud`

## n8n cloud: HTTP “шаги-функции”

Для **n8n cloud** правильный вариант — дергать шаги по HTTP:

- `POST /step/dedupe`
- `POST /step/classify`
- `POST /step/analyze`
- `POST /step/message`
- `POST /step/send_whatsapp`

Формат входа/выхода у шагов:

```json
{ "items": [ { "json": {...}, "binary": {...} } ] }
```

Ожидаемая структура `items[]` (примерно как в Gmail ноде n8n):

- `item.json`: `{ id, threadId, subject, from, to, date, snippet, ... }`
- `item.binary.attachment_0` (если есть вложение): `{ data (base64), fileName, mimeType, fileSize, fileExtension, ... }`

Если задан `GL_API_KEY`, добавляй заголовок `X-API-Key: <ключ>` в HTTP Request нодах.

## Деплой на Railway (минимум возни)

Сервис **задеплоен на Railway** и доступен по публичному URL:

- `https://guaranteelettersservice-production.up.railway.app`
- healthcheck: `GET /health`

Этот URL используй в n8n Cloud в HTTP Request нодах (например: `POST /step/classify` → `https://.../step/classify`).

1) Запушь папку `guarantee_letters_service/` в GitHub (лучше отдельный репозиторий).
2) Railway → New Project → GitHub Repository → выбери репо.
3) В Variables добавь ключи из секции “Переменные окружения” (и `GL_API_KEY`).
4) В Settings сервиса укажи Start Command:

`uvicorn app:app --host 0.0.0.0 --port $PORT`

5) Получившийся публичный URL используй в n8n cloud HTTP Request нодах.
