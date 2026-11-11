import httpx
import asyncio
import logging
from typing import Optional, Dict, Any, List
from multi_agent_system.config import settings, MODELS
from multi_agent_system.agents.orchestrator import orchestrator
from multi_agent_system.db import db

logger = logging.getLogger("telegram_bot")
logging.basicConfig(level=logging.INFO)

class TelegramBot:
    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.TELEGRAM_BOT_TOKEN
        self.api_base = f"https://api.telegram.org/bot{self.token}"
        self.allowed_users = settings.TELEGRAM_ALLOWED_USER_IDS
        self.running = False
        self.last_update_id = 0

    def is_configured(self) -> bool:
        return bool(self.token and len(self.token) > 10)

    async def call_api(self, method: str, data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        if not self.is_configured():
            logger.warning("Telegram Bot Token is not configured.")
            return None

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(f"{self.api_base}/{method}", json=data or {})
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.error(f"Telegram API call error ({method}): {e}")
                return None

    async def send_message(self, chat_id: int, text: str, parse_mode: str = "Markdown", reply_markup: Optional[Dict[str, Any]] = None):
        # Truncate to Telegram's 4096 character limit per message if needed
        chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)]
        for chunk in chunks:
            payload = {
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": parse_mode
            }
            if reply_markup:
                payload["reply_markup"] = reply_markup
            res = await self.call_api("sendMessage", payload)
            if not res:
                # Fallback to plain text if markdown formatting failed
                payload["parse_mode"] = ""
                await self.call_api("sendMessage", payload)

    async def send_chat_action(self, chat_id: int, action: str = "typing"):
        await self.call_api("sendChatAction", {"chat_id": chat_id, "action": action})

    async def process_update(self, update: Dict[str, Any]):
        message = update.get("message")
        if not message:
            return

        chat_id = message["chat"]["id"]
        from_user = message.get("from", {})
        user_id = from_user.get("id")
        user_name = from_user.get("first_name", "Friend")
        text = message.get("text", "").strip()

        # Security check: User ID Whitelist
        if self.allowed_users and user_id not in self.allowed_users:
            await self.send_message(
                chat_id,
                f"⛔ *Unauthorized Access*\n\nYour Telegram User ID is `{user_id}`.\nThis multi-agent bot is locked to authorized users. Add your ID to `TELEGRAM_ALLOWED_USERS` in your server `.env` to unlock.",
                parse_mode="Markdown"
            )
            return

        session_id = f"tg_{chat_id}"

        # Handle Commands
        if text.startswith("/"):
            await self._handle_command(chat_id, session_id, user_name, text)
            return

        # Normal User Query: Send typing indicator while orchestrator processes
        await self.send_chat_action(chat_id, "typing")

        try:
            result = await orchestrator.handle_message(
                session_id=session_id,
                user_id=str(user_id),
                user_message=text,
                platform="telegram"
            )

            response_text = result["response"]
            agent_used = result["agent_used"]
            metadata = result.get("metadata", {})

            # Format footer badge
            footer = f"\n\n⚡ *Unit*: `{agent_used}`"
            if "council" in metadata:
                models_str = ", ".join(metadata["council"]["models_consulted"])
                ms = metadata["council"]["total_pipeline_latency_ms"]
                footer += f"\n👥 *Council*: {models_str} ({ms}ms)"
            elif "single_agent" in metadata:
                ms = metadata["single_agent"].get("latency_ms", 0)
                sim = " [Simulated]" if metadata["single_agent"].get("is_simulated") else ""
                footer += f" ({ms}ms{sim})"

            await self.send_message(chat_id, response_text + footer)

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self.send_message(chat_id, f"⚠️ Error executing multi-agent pipeline: {str(e)}")

    async def _handle_command(self, chat_id: int, session_id: str, user_name: str, cmd_text: str):
        parts = cmd_text.split()
        cmd = parts[0].lower()

        if cmd == "/start":
            msg = (
                f"👋 *Welcome, {user_name}!*\n\n"
                f"You are connected to the *Unified Multi-Agent System*.\n\n"
                f"🤖 *Active Model Collective*:\n"
                f"• *Claude 3.5 Sonnet*: Deep reasoning & architecture\n"
                f"• *Gemini 2.5 Flash*: Fast factual research & broad context\n"
                f"• *GPT-4o*: Step-by-step logic, code & actions\n"
                f"• *Qwen 2.5 72B*: Mathematical precision & coding\n"
                f"• *Kimi k3*: Long-document comprehension & nuance\n\n"
                f"💡 *How to use*:\n"
                f"• Simply type any question: The **Auto-Router** selects the best specialist model.\n"
                f"• For critical decisions, type `council: <your question>` to trigger the **Multi-Agent Council**.\n"
                f"• Use `/mode` to switch routing styles.\n"
                f"• Use `/clear` to reset conversation context."
            )
            await self.send_message(chat_id, msg)

        elif cmd == "/mode":
            if len(parts) > 1:
                new_mode = parts[1].lower()
                valid_modes = ["auto", "council", "claude", "gemini", "chatgpt", "qwen", "kimi"]
                if new_mode in valid_modes:
                    db.update_session_mode(session_id, new_mode)
                    await self.send_message(chat_id, f"✅ Routing mode switched to: *{new_mode.upper()}*")
                else:
                    await self.send_message(chat_id, f"❌ Invalid mode. Choose from: `{', '.join(valid_modes)}`")
            else:
                session = db.get_or_create_session(session_id, str(chat_id), "telegram")
                current = session.get("mode", "auto")
                await self.send_message(
                    chat_id,
                    f"⚙️ Current Mode: *{current.upper()}*\n\n"
                    f"To change mode, use:\n"
                    f"• `/mode auto` (Smart Router chooses model)\n"
                    f"• `/mode council` (All 5 models evaluate & synthesize)\n"
                    f"• `/mode claude` (Pin Claude 3.5 Sonnet)\n"
                    f"• `/mode gemini` (Pin Gemini 2.5 Flash)\n"
                    f"• `/mode chatgpt` (Pin GPT-4o)\n"
                    f"• `/mode qwen` (Pin Qwen 2.5 72B)\n"
                    f"• `/mode kimi` (Pin Kimi k3)"
                )

        elif cmd == "/clear":
            db.clear_history(session_id)
            await self.send_message(chat_id, "🧹 Conversation context cleared! Memory is reset.")

        elif cmd == "/status":
            session = db.get_or_create_session(session_id, str(chat_id), "telegram")
            history = db.get_history(session_id, limit=20)
            status_msg = (
                f"📊 *Multi-Agent System Telemetry*\n\n"
                f"• *Status*: 🟢 24/7 Online\n"
                f"• *Active Session*: `{session_id}`\n"
                f"• *Current Routing Mode*: `{session.get('mode', 'auto')}`\n"
                f"• *Stored Context Turns*: `{len(history)}`\n"
                f"• *Registered Models*: `{len(MODELS)} models ready`\n"
                f"• *Mock Fallback Allowed*: `{settings.ALLOW_MOCK_FALLBACK}`\n"
            )
            await self.send_message(chat_id, status_msg)

        elif cmd == "/help":
            help_msg = (
                f"📖 *Command Guide*\n\n"
                f"/start - Intro & architecture overview\n"
                f"/mode [mode] - View or switch routing mode\n"
                f"/status - System health & telemetry\n"
                f"/clear - Reset conversational memory\n"
                f"/help - This manual"
            )
            await self.send_message(chat_id, help_msg)

    async def start_polling(self):
        if not self.is_configured():
            logger.info("Telegram Bot token not provided. Polling disabled (configure TELEGRAM_BOT_TOKEN in .env).")
            return

        self.running = True
        logger.info("Telegram Bot long polling started...")

        while self.running:
            try:
                updates_res = await self.call_api("getUpdates", {
                    "offset": self.last_update_id + 1,
                    "timeout": 20
                })
                if updates_res and updates_res.get("ok"):
                    for update in updates_res.get("result", []):
                        self.last_update_id = update["update_id"]
                        await self.process_update(update)
            except Exception as e:
                logger.error(f"Polling loop error: {e}")
                await asyncio.sleep(5)
            await asyncio.sleep(0.5)

    def stop_polling(self):
        self.running = False

telegram_bot = TelegramBot()
