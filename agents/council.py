import asyncio
import time
from typing import List, Dict, Any, Optional
from multi_agent_system.models.gateway import gateway, ModelResponse
from multi_agent_system.agents.specialists import SPECIALIST_SYSTEM_PROMPTS
from multi_agent_system.config import MODELS

class CouncilSynthesizer:
    def __init__(self):
        pass

    async def run_council(
        self,
        participating_models: List[str],
        messages: List[Dict[str, str]],
        synthesizer_model: str = "claude"
    ) -> Dict[str, Any]:
        start_time = time.time()

        # Step 1: Run all participating models in parallel
        tasks = []
        for model_key in participating_models:
            sys_prompt = SPECIALIST_SYSTEM_PROMPTS.get(model_key)
            tasks.append(
                gateway.generate(
                    model_key=model_key,
                    messages=messages,
                    system_instruction=sys_prompt
                )
            )

        responses: List[ModelResponse] = await asyncio.gather(*tasks, return_exceptions=False)
        total_parallel_latency = (time.time() - start_time) * 1000

        # Step 2: Prepare inputs for the consensus synthesis
        individual_outputs = []
        model_summaries = {}
        total_tokens = 0

        for r in responses:
            individual_outputs.append(f"### Perspective: {r.model_name} ({r.model_key})\n{r.content}\n")
            model_summaries[r.model_key] = {
                "name": r.model_name,
                "latency_ms": r.latency_ms,
                "is_simulated": r.is_simulated,
                "tokens": r.tokens
            }
            total_tokens += r.tokens.get("total", 0)

        # Step 3: Run the Synthesizer/Adjudicator
        combined_perspectives = "\n".join(individual_outputs)
        user_query = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")

        synthesis_prompt = f"""You are the Master Council Synthesizer.
The user asked: "{user_query}"

Below are independent analyses from different AI specialist models:
{combined_perspectives}

Your mission as a unified AI unit:
1. Synthesize a single, clear, definitive master answer that reconciles all valid points.
2. Highlight unique insights contributed by individual specialists (e.g. "Claude noted...", "Qwen optimized...").
3. Flag any discrepancies, conflicting points, or potential hallucinations caught during cross-verification.
4. Output a well-formatted, complete response for the user."""

        synth_messages = [{"role": "user", "content": synthesis_prompt}]
        synth_response: ModelResponse = await gateway.generate(
            model_key=synthesizer_model,
            messages=synth_messages,
            system_instruction="You are the lead orchestrator uniting multiple AI models into a single cohesive response.",
            temperature=0.4
        )

        overall_time = (time.time() - start_time) * 1000

        return {
            "master_response": synth_response.content,
            "individual_perspectives": {r.model_key: r.content for r in responses},
            "telemetry": {
                "parallel_latency_ms": round(total_parallel_latency, 2),
                "total_pipeline_latency_ms": round(overall_time, 2),
                "models_consulted": [r.model_name for r in responses],
                "synthesizer": MODELS.get(synthesizer_model, None).name if synthesizer_model in MODELS else synthesizer_model,
                "model_telemetry": model_summaries,
                "total_tokens_estimated": total_tokens + synth_response.tokens.get("total", 0)
            }
        }

council = CouncilSynthesizer()
