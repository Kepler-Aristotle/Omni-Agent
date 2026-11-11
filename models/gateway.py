import httpx
import json
import time
import asyncio
from typing import List, Dict, Any, Optional
from multi_agent_system.config import settings, MODELS, ModelConfig

class ModelResponse:
    def __init__(self, model_key: str, content: str, latency_ms: float, is_simulated: bool = False, tokens: Optional[Dict[str, int]] = None):
        self.model_key = model_key
        self.model_name = MODELS.get(model_key, ModelConfig(name=model_key, provider="", model_id="", endpoint="", strengths=[])).name
        self.content = content
        self.latency_ms = latency_ms
        self.is_simulated = is_simulated
        self.tokens = tokens or {"prompt": 0, "completion": 0, "total": 0}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_key": self.model_key,
            "model_name": self.model_name,
            "content": self.content,
            "latency_ms": round(self.latency_ms, 2),
            "is_simulated": self.is_simulated,
            "tokens": self.tokens
        }

class UnifiedModelGateway:
    def __init__(self):
        self.timeout = httpx.Timeout(45.0, connect=10.0)

    async def generate(
        self,
        model_key: str,
        messages: List[Dict[str, str]],
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 1500
    ) -> ModelResponse:
        model_cfg = MODELS.get(model_key)
        if not model_cfg:
            raise ValueError(f"Unknown model key: {model_key}")

        temp = temperature if temperature is not None else model_cfg.recommended_temperature
        start_time = time.time()

        # Check if we should use OpenRouter as a universal proxy
        if settings.OPENROUTER_API_KEY:
            try:
                return await self._call_openrouter(model_key, model_cfg, messages, system_instruction, temp, max_tokens, start_time)
            except Exception as e:
                # If OpenRouter fails, continue to direct provider or simulation
                pass

        # Try direct provider API
        try:
            if model_cfg.provider == "anthropic" and settings.ANTHROPIC_API_KEY:
                return await self._call_anthropic(model_cfg, messages, system_instruction, temp, max_tokens, start_time)
            elif model_cfg.provider == "google" and settings.GEMINI_API_KEY:
                return await self._call_gemini(model_cfg, messages, system_instruction, temp, max_tokens, start_time)
            elif model_cfg.provider in ("openai", "alibaba", "moonshot"):
                api_key = (
                    settings.OPENAI_API_KEY if model_cfg.provider == "openai"
                    else settings.DASHSCOPE_API_KEY if model_cfg.provider == "alibaba"
                    else settings.MOONSHOT_API_KEY
                )
                if api_key:
                    return await self._call_openai_compatible(model_key, model_cfg, api_key, messages, system_instruction, temp, max_tokens, start_time)
        except Exception as e:
            if not settings.ALLOW_MOCK_FALLBACK:
                raise e

        # If no API key is provided or live call failed and mock is allowed:
        if settings.ALLOW_MOCK_FALLBACK:
            return self._generate_simulated_response(model_key, model_cfg, messages, system_instruction, start_time)

        raise RuntimeError(f"No API key available for {model_cfg.name} and mock fallback is disabled.")

    async def _call_openrouter(self, model_key: str, cfg: ModelConfig, messages: List[Dict[str, str]], sys_inst: Optional[str], temp: float, max_tokens: int, start_time: float) -> ModelResponse:
        model_map = {
            "claude": "anthropic/claude-3.5-sonnet",
            "gemini": "google/gemini-2.5-flash",
            "chatgpt": "openai/gpt-4o",
            "qwen": "qwen/qwen-2.5-72b-instruct",
            "kimi": "moonshotai/moonshot-v1-128k"
        }
        router_model = model_map.get(model_key, cfg.model_id)
        formatted_msgs = []
        if sys_inst:
            formatted_msgs.append({"role": "system", "content": sys_inst})
        formatted_msgs.extend(messages)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": router_model,
                    "messages": formatted_msgs,
                    "temperature": temp,
                    "max_tokens": max_tokens
                }
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return ModelResponse(
                model_key=model_key,
                content=content,
                latency_ms=(time.time() - start_time) * 1000,
                is_simulated=False,
                tokens={
                    "prompt": usage.get("prompt_tokens", 0),
                    "completion": usage.get("completion_tokens", 0),
                    "total": usage.get("total_tokens", 0)
                }
            )

    async def _call_anthropic(self, cfg: ModelConfig, messages: List[Dict[str, str]], sys_inst: Optional[str], temp: float, max_tokens: int, start_time: float) -> ModelResponse:
        # Convert messages to Anthropic format (roles: user, assistant)
        anthropic_msgs = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] in ("user", "assistant")]
        payload: Dict[str, Any] = {
            "model": cfg.model_id,
            "messages": anthropic_msgs,
            "max_tokens": max_tokens,
            "temperature": temp
        }
        if sys_inst:
            payload["system"] = sys_inst

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                cfg.endpoint,
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            resp.raise_for_status()
            data = resp.json()
            content = "".join([block.get("text", "") for block in data.get("content", [])])
            usage = data.get("usage", {})
            return ModelResponse(
                model_key="claude",
                content=content,
                latency_ms=(time.time() - start_time) * 1000,
                is_simulated=False,
                tokens={
                    "prompt": usage.get("input_tokens", 0),
                    "completion": usage.get("output_tokens", 0),
                    "total": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                }
            )

    async def _call_gemini(self, cfg: ModelConfig, messages: List[Dict[str, str]], sys_inst: Optional[str], temp: float, max_tokens: int, start_time: float) -> ModelResponse:
        url = f"{cfg.endpoint}/{cfg.model_id}:generateContent?key={settings.GEMINI_API_KEY}"
        contents = []
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temp,
                "maxOutputTokens": max_tokens
            }
        }
        if sys_inst:
            payload["systemInstruction"] = {"parts": [{"text": sys_inst}]}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers={"Content-Type": "application/json"}, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            content = ""
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                content = "".join([p.get("text", "") for p in parts])
            usage = data.get("usageMetadata", {})
            return ModelResponse(
                model_key="gemini",
                content=content,
                latency_ms=(time.time() - start_time) * 1000,
                is_simulated=False,
                tokens={
                    "prompt": usage.get("promptTokenCount", 0),
                    "completion": usage.get("candidatesTokenCount", 0),
                    "total": usage.get("totalTokenCount", 0)
                }
            )

    async def _call_openai_compatible(self, model_key: str, cfg: ModelConfig, api_key: str, messages: List[Dict[str, str]], sys_inst: Optional[str], temp: float, max_tokens: int, start_time: float) -> ModelResponse:
        formatted_msgs = []
        if sys_inst:
            formatted_msgs.append({"role": "system", "content": sys_inst})
        formatted_msgs.extend(messages)

        payload = {
            "model": cfg.model_id,
            "messages": formatted_msgs,
            "temperature": temp,
            "max_tokens": max_tokens
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                cfg.endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return ModelResponse(
                model_key=model_key,
                content=content,
                latency_ms=(time.time() - start_time) * 1000,
                is_simulated=False,
                tokens={
                    "prompt": usage.get("prompt_tokens", 0),
                    "completion": usage.get("completion_tokens", 0),
                    "total": usage.get("total_tokens", 0)
                }
            )

    def _generate_simulated_response(self, model_key: str, cfg: ModelConfig, messages: List[Dict[str, str]], sys_inst: Optional[str], start_time: float) -> ModelResponse:
        latest_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        
        simulated_templates = {
            "claude": f"[Claude 3.5 Sonnet Perspective]\nFocus: Architectural rigor & deep analysis.\nAnalyzing '{latest_user_msg}':\n1. Systematic breakdown of primary objectives\n2. Validation of safety and structural constraints\n3. High-confidence recommendation with risk mitigations.",
            "gemini": f"[Gemini 2.5 Flash Perspective]\nFocus: Broad synthesis & rapid factual recall.\nRegarding '{latest_user_msg}':\n• Multimodal & cross-domain context integrated\n• Key factual points and fast reference benchmarks verified\n• Comprehensive coverage across relevant sources.",
            "chatgpt": f"[GPT-4o Perspective]\nFocus: Pragmatic logic, structured actions & code.\nAddressing '{latest_user_msg}':\n- Practical action plan and step-by-step logic\n- Clean execution pattern ready for real-world deployment\n- Direct response formatted for immediate utility.",
            "qwen": f"[Qwen 2.5 72B Perspective]\nFocus: Algorithmic precision, math & technical details.\nTechnical analysis for '{latest_user_msg}':\n• High algorithmic fidelity and verified equations\n• Edge-case analysis and computational optimizations applied.",
            "kimi": f"[Kimi k3 Perspective]\nFocus: Ultra-long context comprehension & deep research.\nDeep dive into '{latest_user_msg}':\n• Full historical context retained across lengthy conversation tracks\n• Nuanced multi-layered perspective incorporating referenced domain papers."
        }

        content = simulated_templates.get(model_key, f"[{cfg.name}] Processed: {latest_user_msg}")
        latency = (time.time() - start_time) * 1000 + 120.0 # simulated 120ms roundtrip

        return ModelResponse(
            model_key=model_key,
            content=content,
            latency_ms=latency,
            is_simulated=True,
            tokens={"prompt": 64, "completion": 110, "total": 174}
        )

gateway = UnifiedModelGateway()
