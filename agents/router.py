import re
from typing import Dict, Any, List, Tuple
from pydantic import BaseModel

class RouteDecision(BaseModel):
    strategy: str # 'single_best', 'council_consensus', 'collaborative_pipeline'
    primary_model: str # e.g. 'claude', 'gemini', 'chatgpt', 'qwen', 'kimi'
    participating_models: List[str]
    domain: str # 'coding', 'math', 'reasoning', 'factual', 'creative', 'general'
    complexity: str # 'simple', 'moderate', 'complex'
    reasoning: str

class AgentRouter:
    def __init__(self):
        # Keyword & pattern heuristics for domain mapping
        self.code_patterns = re.compile(
            r'(?:c\+\+|cpp|\b(?:code|coding|python|javascript|typescript|java|golang|rust|bug|error|function|class|algorithm|tree|binary|graph|sort|sql|docker|git|api|implement|script)\b)',
            re.IGNORECASE
        )
        self.math_patterns = re.compile(
            r'\b(?:math|mathematics|equation|calculate|probability|matrix|integral|derivative|formula|solve|proof|algebra|calculus)\b',
            re.IGNORECASE
        )
        self.reasoning_patterns = re.compile(
            r'\b(?:architecture|compare|contrast|tradeoff|analyze|design|strategy|evaluate|review|critique|why|trade-off|scalability)\b',
            re.IGNORECASE
        )
        self.factual_patterns = re.compile(
            r'\b(?:what is|who is|when did|history|summary|explain|define|facts|news|research|paper|discovery|overview)\b',
            re.IGNORECASE
        )
        self.creative_patterns = re.compile(
            r'\b(?:write a story|poem|essay|persona|roleplay|brainstorm|pitch|email|dialogue|creative)\b',
            re.IGNORECASE
        )
        self.council_triggers = re.compile(
            r'\b(?:council|all models|consensus|compare all|debate|cross-check|verify thoroughly|critical)\b',
            re.IGNORECASE
        )

    def route(self, user_query: str, forced_mode: str = "auto") -> RouteDecision:
        query_len = len(user_query.split())
        
        # If user explicitly selected a specific model or council mode
        if forced_mode in ("claude", "gemini", "chatgpt", "qwen", "kimi"):
            return RouteDecision(
                strategy="single_best",
                primary_model=forced_mode,
                participating_models=[forced_mode],
                domain="user_forced",
                complexity="user_defined",
                reasoning=f"User manually pinned model to {forced_mode}."
            )
        elif forced_mode == "council":
            return RouteDecision(
                strategy="council_consensus",
                primary_model="claude",
                participating_models=["claude", "gemini", "chatgpt", "qwen", "kimi"],
                domain="multi_agent_consensus",
                complexity="complex",
                reasoning="User manually selected Council mode across all 5 models."
            )

        # Automatic Classification
        if self.council_triggers.search(user_query) or query_len > 80:
            return RouteDecision(
                strategy="council_consensus",
                primary_model="claude",
                participating_models=["claude", "gemini", "chatgpt", "qwen"],
                domain="deep_evaluation",
                complexity="complex",
                reasoning="Query has high complexity or explicit multi-model consensus trigger."
            )

        if self.code_patterns.search(user_query):
            return RouteDecision(
                strategy="single_best",
                primary_model="qwen", # Qwen 2.5 72B is phenomenal at coding
                participating_models=["qwen", "claude"],
                domain="coding",
                complexity="moderate",
                reasoning="Coding inquiry assigned to Qwen with Claude fallback review."
            )

        if self.math_patterns.search(user_query):
            return RouteDecision(
                strategy="single_best",
                primary_model="qwen",
                participating_models=["qwen", "chatgpt"],
                domain="math",
                complexity="moderate",
                reasoning="Mathematical inquiry assigned to Qwen 2.5."
            )

        if self.reasoning_patterns.search(user_query):
            return RouteDecision(
                strategy="single_best",
                primary_model="claude",
                participating_models=["claude", "gemini"],
                domain="reasoning",
                complexity="moderate",
                reasoning="System design or reasoning inquiry routed to Claude 3.5 Sonnet."
            )

        if self.factual_patterns.search(user_query):
            return RouteDecision(
                strategy="single_best",
                primary_model="gemini",
                participating_models=["gemini", "kimi"],
                domain="factual",
                complexity="simple",
                reasoning="Factual or research query assigned to Gemini 2.5 Flash."
            )

        # Default general path
        return RouteDecision(
            strategy="single_best",
            primary_model="chatgpt",
            participating_models=["chatgpt", "gemini"],
            domain="general",
            complexity="simple",
            reasoning="General conversation routed to GPT-4o."
        )

router = AgentRouter()
