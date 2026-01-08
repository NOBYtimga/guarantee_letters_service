from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException

from gl_service.api_models import N8nItemsRequest, N8nItemsResponse, N8nSendResponse
from gl_service.n8n_adapter import email_from_n8n_item
from gl_service.settings import settings
from gl_service.steps import (
    step_analyze_attachment,
    step_build_message,
    step_classify,
    step_dedupe_latest,
    step_no_attachment_fallback,
)
from gl_service.whapi_client import send_text_and_optional_doc


app = FastAPI(title="Guarantee Letters Service", version="0.1.0")


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    if not settings.api_key:
        return
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# --- n8n-friendly “step” endpoints (для оркестрации n8n cloud через HTTP Request) ---


@app.post("/step/dedupe", response_model=N8nItemsResponse)
async def step_dedupe(req: N8nItemsRequest, _: None = Depends(require_api_key)) -> N8nItemsResponse:
    emails = [email_from_n8n_item(it) for it in req.items]
    kept, dropped = step_dedupe_latest(emails)
    # Возвращаем в исходном формате item-ов (как минимум json-часть + binary если был)
    out_items = []
    kept_ids = {e.id for e in kept}
    for it in req.items:
        eid = str((it.get("json") or {}).get("id") or "")
        if eid in kept_ids:
            out_items.append(it)
    return N8nItemsResponse(items=out_items, meta={"dropped": dropped})


@app.post("/step/classify", response_model=N8nItemsResponse)
async def step_classify_api(req: N8nItemsRequest, _: None = Depends(require_api_key)) -> N8nItemsResponse:
    out = []
    for it in req.items:
        email = email_from_n8n_item(it)
        res = await step_classify(email)
        it2 = dict(it)
        it2["json"] = dict(it2.get("json") or {})
        it2["json"]["is_guarantee_letter"] = res.is_guarantee_letter
        out.append(it2)
    return N8nItemsResponse(items=out)


@app.post("/step/analyze", response_model=N8nItemsResponse)
async def step_analyze_api(req: N8nItemsRequest, _: None = Depends(require_api_key)) -> N8nItemsResponse:
    out = []
    for it in req.items:
        email = email_from_n8n_item(it)
        ai, _att = await step_analyze_attachment(email)
        if ai is None:
            ai = step_no_attachment_fallback(email)
        it2 = dict(it)
        it2["json"] = dict(it2.get("json") or {})
        it2["json"]["ai_response"] = ai.model_dump()
        it2["json"]["has_attachment"] = email.attachment is not None
        out.append(it2)
    return N8nItemsResponse(items=out)


@app.post("/step/message", response_model=N8nItemsResponse)
async def step_message_api(req: N8nItemsRequest, _: None = Depends(require_api_key)) -> N8nItemsResponse:
    from gl_service.models import GuaranteeDocExtract

    out = []
    for it in req.items:
        js = it.get("json") or {}
        ai = js.get("ai_response")
        ai_obj = None if ai is None else GuaranteeDocExtract.model_validate(ai)
        msg = step_build_message(ai_obj)
        it2 = dict(it)
        it2["json"] = dict(it2.get("json") or {})
        it2["json"]["message_text"] = msg
        out.append(it2)
    return N8nItemsResponse(items=out)


@app.post("/step/send_whatsapp", response_model=N8nSendResponse)
async def step_send_whatsapp_api(
    req: N8nItemsRequest, _: None = Depends(require_api_key)
) -> N8nSendResponse:
    if not settings.whapi_to:
        raise HTTPException(status_code=400, detail="GL_WHAPI_TO is not set")

    sent = []
    for it in req.items:
        js = it.get("json") or {}
        body = js.get("message_text") or ""
        if not body:
            continue
        email = email_from_n8n_item(it)
        res = await send_text_and_optional_doc(
            to=settings.whapi_to,
            text=body,
            attachment=email.attachment,
        )
        sent.append(res.model_dump())
    return N8nSendResponse(sent=sent)


