import os
import sys
import uvicorn
from multi_agent_system.config import settings

def main():
    print("=" * 60)
    print("🚀 UNIFIED MULTI-AGENT SYSTEM INITIALIZING")
    print(f"• App: {settings.APP_NAME}")
    print(f"• Listening: http://{settings.HOST}:{settings.PORT}")
    print(f"• Environment: {settings.ENV}")
    print(f"• Telegram Integration: {'Configured' if settings.TELEGRAM_BOT_TOKEN else 'Waiting for token in .env'}")
    print("=" * 60)

    uvicorn.run(
        "multi_agent_system.mobile.web_server:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=(settings.ENV == "development"),
        log_level="info"
    )

if __name__ == "__main__":
    main()
