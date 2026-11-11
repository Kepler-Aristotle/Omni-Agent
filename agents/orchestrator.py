from typing import Dict, Any, List, Optional
from multi_agent_system.db import db
from multi_agent_system.agents.router import router, RouteDecision
from multi_agent_system.agents.council import council
from multi_agent_system.agents.specialists import SPECIALIST_SYSTEM_PROMPTS
from multi_agent_system.models.gateway import gateway, ModelResponse

class MasterOrchestrator:
    def __init__(self):
        pass

    async def handle_message(
        self,
        session_id: str,
        user_id: str,
        user_message: str,
        platform: str = "web",
        override_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        # 1. Ensure session exists
        session = db.get_or_create_session(session_id, user_id, platform)
        active_mode = override_mode or session.get("mode", "auto")

        # 2. Save user message to database
        db.add_message(session_id, role="user", content=user_message)

        # 3. Retrieve conversation history
        raw_history = db.get_history(session_id, limit=8)
        formatted_messages = [{"role": m["role"], "content": m["content"]} for m in raw_history]

        # 4. Route task
        route: RouteDecision = router.route(user_message, forced_mode=active_mode)

        response_content = ""
        agent_tag = ""
        metadata: Dict[str, Any] = {
            "route": route.dict(),
            "session_id": session_id,
            "mode": active_mode
        }

        # 5. Execute according to chosen strategy
        if route.strategy == "council_consensus":
            council_result = await council.run_council(
                participating_models=route.participating_models,
                messages=formatted_messages,
                synthesizer_model="claude"
            )
            response_content = council_result["master_response"]
            agent_tag = f"council[{'+'.join(route.participating_models)}]"
            metadata["council"] = council_result["telemetry"]
            metadata["individual_perspectives"] = council_result["individual_perspectives"]

        elif route.strategy == "collaborative_pipeline":
            # Primary model drafts, secondary model reviews
            primary = route.primary_model
            reviewer = route.participating_models[1] if len(route.participating_models) > 1 else "claude"

            # Step A: Primary draft
            draft_resp: ModelResponse = await gateway.generate(
                model_key=primary,
                messages=formatted_messages,
                system_instruction=SPECIALIST_SYSTEM_PROMPTS.get(primary)
            )

            # Step B: Review & Refine
            review_prompt = f"Review and refine the following draft produced by {primary} for the query '{user_message}':\n\n{draft_resp.content}\n\nDeliver the polished final version."
            rev_msgs = [{"role": "user", "content": review_prompt}]
            final_resp: ModelResponse = await gateway.generate(
                model_key=reviewer,
                messages=rev_msgs,
                system_instruction=SPECIALIST_SYSTEM_PROMPTS.get(reviewer)
            )

            response_content = final_resp.content
            agent_tag = f"pipeline[{primary}->{reviewer}]"
            metadata["pipeline"] = {
                "drafter": draft_resp.to_dict(),
                "reviewer": final_resp.to_dict()
            }

        else: # single_best
            model_key = route.primary_model
            model_resp: ModelResponse = await gateway.generate(
                model_key=model_key,
                messages=formatted_messages,
                system_instruction=SPECIALIST_SYSTEM_PROMPTS.get(model_key)
            )
            response_content = model_resp.content
            agent_tag = model_key
            metadata["single_agent"] = model_resp.to_dict()

        # 6. Save assistant output to database
        db.add_message(session_id, role="assistant", content=response_content, agent_used=agent_tag, metadata=metadata)

        return {
            "session_id": session_id,
            "response": response_content,
            "agent_used": agent_tag,
            "metadata": metadata
        }

orchestrator = MasterOrchestrator()
