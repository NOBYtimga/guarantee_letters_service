from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class N8nItemsRequest(BaseModel):
    """
    Универсальный формат для n8n cloud:
    {
      "items": [ { "json": {...}, "binary": {...} }, ... ]
    }
    """

    items: list[dict[str, Any]] = Field(default_factory=list)


class N8nItemsResponse(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class N8nSendResponse(BaseModel):
    sent: list[dict[str, Any]] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


