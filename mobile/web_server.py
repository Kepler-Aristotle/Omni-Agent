import os
import asyncio
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from multi_agent_system.config import settings, MODELS
from multi_agent_system.agents.orchestrator import orchestrator
from multi_agent_system.db import db
from multi_agent_system.mobile.telegram_bot import telegram_bot

app = FastAPI(title="Unified Multi-Agent System", version="1.0.0")

class ChatRequest(BaseModel):
    session_id: str = "mobile_default"
    user_id: str = "mobile_user"
    message: str
    mode: Optional[str] = "auto"
    auth_token: Optional[str] = None

class ModeRequest(BaseModel):
    session_id: str
    mode: str

@app.on_event("startup")
async def on_startup():
    # If a Telegram bot token is present and no webhook URL is forced, start background polling
    if telegram_bot.is_configured():
        asyncio.create_task(telegram_bot.start_polling())

@app.on_event("shutdown")
async def on_shutdown():
    telegram_bot.stop_polling()

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    static_file = os.path.join(os.path.dirname(__file__), "..", "static", "index.html")
    if os.path.exists(static_file):
        with open(static_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Multi-Agent System Online</h1><p>Static interface loading...</p>")

@app.get("/api/status")
async def get_status():
    return {
        "status": "online",
        "app_name": settings.APP_NAME,
        "environment": settings.ENV,
        "telegram_configured": telegram_bot.is_configured(),
        "registered_models": {
            k: {
                "name": v.name,
                "provider": v.provider,
                "strengths": v.strengths,
                "context_window": v.context_window
            }
            for k, v in MODELS.items()
        },
        "mock_fallback_allowed": settings.ALLOW_MOCK_FALLBACK
    }

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    # Optional Security PIN/Token check for college mobile access
    if settings.SECRET_KEY and req.auth_token and req.auth_token != settings.SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid Authentication Token")

    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Empty message")

    try:
        result = await orchestrator.handle_message(
            session_id=req.session_id,
            user_id=req.user_id,
            user_message=req.message,
            platform="web_mobile",
            override_mode=req.mode if req.mode != "auto" else None
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history")
async def get_history(session_id: str = "mobile_default", limit: int = 15):
    return {
        "session_id": session_id,
        "messages": db.get_history(session_id, limit=limit)
    }

@app.post("/api/mode")
async def update_mode(req: ModeRequest):
    valid_modes = ["auto", "council", "claude", "gemini", "chatgpt", "qwen", "kimi"]
    if req.mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Invalid mode. Must be one of: {valid_modes}")
    db.update_session_mode(req.session_id, req.mode)
    return {"status": "success", "mode": req.mode}

@app.post("/api/clear")
async def clear_session(session_id: str = "mobile_default"):
    db.clear_history(session_id)
    return {"status": "cleared", "session_id": session_id}

@app.post("/api/telegram-webhook")
async def telegram_webhook(req: Request):
    if not telegram_bot.is_configured():
        return JSONResponse({"status": "ignored", "reason": "bot not configured"})
    try:
        payload = await req.json()
        await telegram_bot.process_update(payload)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
