import os
from typing import Dict, Any, List
from pydantic import BaseModel, Field

class ModelConfig(BaseModel):
    name: str
    provider: str
    model_id: str
    endpoint: str
    strengths: List[str]
    context_window: int = 128000
    supports_vision: bool = True
    recommended_temperature: float = 0.7

class Settings(BaseModel):
    # App Settings
    APP_NAME: str = "Unified Multi-Agent System"
    ENV: str = os.getenv("APP_ENV", "development")
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-mobile-token-2026")
    
    # Telegram Bot Settings (For Mobile Access)
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_ALLOWED_USER_IDS: List[int] = Field(
        default_factory=lambda: [int(x.strip()) for x in os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",") if x.strip().isdigit()]
    )
    
    # Model API Keys (Supports direct provider keys or a unified OpenRouter key)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")  # Qwen
    MOONSHOT_API_KEY: str = os.getenv("MOONSHOT_API_KEY", "")    # Kimi
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "") # Universal proxy option
    
    # Simulation / Mock Mode for local testing when keys are not yet provided
    ALLOW_MOCK_FALLBACK: bool = True
    
    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "multi_agent.db")

# Pre-configured Model Registry
MODELS: Dict[str, ModelConfig] = {
    "claude": ModelConfig(
        name="Claude 3.5 Sonnet",
        provider="anthropic",
        model_id="claude-3-5-sonnet-20241022",
        endpoint="https://api.anthropic.com/v1/messages",
        strengths=["deep_reasoning", "system_architecture", "code_review", "nuanced_writing", "safety"],
        context_window=200000,
        recommended_temperature=0.3
    ),
    "gemini": ModelConfig(
        name="Gemini 2.5 Flash",
        provider="google",
        model_id="gemini-2.5-flash",
        endpoint="https://generativelanguage.googleapis.com/v1beta/models",
        strengths=["fast_search", "large_documents", "multimodal_analysis", "broad_knowledge"],
        context_window=1000000,
        recommended_temperature=0.7
    ),
    "chatgpt": ModelConfig(
        name="GPT-4o",
        provider="openai",
        model_id="gpt-4o",
        endpoint="https://api.openai.com/v1/chat/completions",
        strengths=["general_logic", "structured_json", "python_execution", "instruction_following"],
        context_window=128000,
        recommended_temperature=0.6
    ),
    "qwen": ModelConfig(
        name="Qwen 2.5 72B",
        provider="alibaba",
        model_id="qwen-2.5-72b-instruct",
        endpoint="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        strengths=["coding_algorithms", "mathematics", "multilingual", "open_weights_fidelity"],
        context_window=131072,
        recommended_temperature=0.5
    ),
    "kimi": ModelConfig(
        name="Kimi k3 / Moonshot v1",
        provider="moonshot",
        model_id="moonshot-v1-128k",
        endpoint="https://api.moonshot.cn/v1/chat/completions",
        strengths=["ultra_long_context", "academic_papers", "deep_document_search", "cross_lingual_nuance"],
        context_window=128000,
        recommended_temperature=0.4
    )
}

settings = Settings()
