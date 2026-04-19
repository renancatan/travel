from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from services.api.app.core.llm_router import MultiProviderRouter
from services.api.app.core.media_metadata import get_media_tooling_status
from services.api.app.core.settings import get_settings
from services.api.app.models.api import AskRequest, AskResponse
from services.api.app.routers.albums import router as albums_router

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(albums_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


@app.get("/runtime")
def runtime() -> dict[str, object]:
    return {
        "app_name": settings.app_name,
        "default_model_alias": settings.copilot_default_model_alias,
        "storage_backend": settings.storage_backend,
        "queue_backend": settings.queue_backend,
        "local_storage_root": settings.local_storage_root,
        "media_tooling": get_media_tooling_status(),
        "editor_limits": {
            "max_reel_clip_duration_seconds": settings.max_reel_clip_duration_seconds,
        },
        "providers": {
            "gemini_configured": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
            "azure_gpt4_configured": bool(
                os.getenv("AZURE_OPENAI_GPT4_ENDPOINT")
                and os.getenv("AZURE_OPENAI_GPT4_API_KEY")
                and os.getenv("AZURE_OPENAI_GPT4_DEPLOYMENT")
            ),
            "azure_gpt5_configured": bool(
                os.getenv("AZURE_OPENAI_GPT5_ENDPOINT")
                and os.getenv("AZURE_OPENAI_GPT5_API_KEY")
                and os.getenv("AZURE_OPENAI_GPT5_DEPLOYMENT")
            ),
        },
    }


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    router = MultiProviderRouter()

    try:
        if request.json_mode:
            answer: str | dict = router.ask_json(request.prompt, model_alias=request.model)
        else:
            answer = router.ask_text(request.prompt, model_alias=request.model)
    except Exception as exc:  # pragma: no cover - integration path
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return AskResponse(answer=answer, route=router.get_last_resolution())
