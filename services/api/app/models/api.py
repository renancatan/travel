from __future__ import annotations

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    prompt: str = Field(min_length=1, description="Prompt sent to the model.")
    model: str | None = Field(default=None, description="Optional model alias: ggl2, gpt4, or gpt5.")
    json_mode: bool = Field(default=False, description="Whether to request JSON output.")


class AskResponse(BaseModel):
    answer: str | dict
    route: dict | None

