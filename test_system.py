import asyncio
import unittest
import uuid
from fastapi.testclient import TestClient

from multi_agent_system.config import settings, MODELS
from multi_agent_system.db import db
from multi_agent_system.agents.router import router, RouteDecision
from multi_agent_system.agents.council import council
from multi_agent_system.agents.orchestrator import orchestrator
from multi_agent_system.mobile.web_server import app

class TestMultiAgentSystem(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.test_session = f"test_session_{uuid.uuid4().hex[:8]}"
        self.test_user = "test_user_id"
        self.client = TestClient(app)

    def test_model_registry(self):
        """Verify all 5 required frontier & open models are registered."""
        expected_models = ["claude", "gemini", "chatgpt", "qwen", "kimi"]
        for m in expected_models:
            self.assertIn(m, MODELS, f"Model {m} must be in MODELS registry")
            cfg = MODELS[m]
            self.assertTrue(len(cfg.strengths) > 0)
            self.assertTrue(cfg.context_window >= 128000)

    def test_router_heuristics(self):
        """Verify task router correctly identifies domains and models."""
        # Coding -> Qwen
        r1 = router.route("Write a binary search tree in C++ with deletion")
        self.assertEqual(r1.primary_model, "qwen")
        self.assertEqual(r1.domain, "coding")

        # System design / reasoning -> Claude
        r2 = router.route("Compare the architectural tradeoffs and failure modes of distributed microservices")
        self.assertEqual(r2.primary_model, "claude")
        self.assertEqual(r2.domain, "reasoning")

        # Factual research -> Gemini
        r3 = router.route("What is the history and discovery of the cosmic microwave background?")
        self.assertEqual(r3.primary_model, "gemini")
        self.assertEqual(r3.domain, "factual")

        # Explicit council trigger
        r4 = router.route("council: What is the optimal database for high throughput real time analytics?")
        self.assertEqual(r4.strategy, "council_consensus")
        self.assertIn("claude", r4.participating_models)
        self.assertIn("gemini", r4.participating_models)
        self.assertIn("chatgpt", r4.participating_models)

    async def test_council_consensus_execution(self):
        """Verify parallel execution of models and consensus synthesis."""
        participating = ["claude", "gemini", "chatgpt", "qwen", "kimi"]
        messages = [{"role": "user", "content": "How do we prevent distributed deadlock?"}]
        result = await council.run_council(participating, messages, synthesizer_model="claude")

        self.assertIn("master_response", result)
        self.assertIn("telemetry", result)
        self.assertEqual(len(result["telemetry"]["models_consulted"]), 5)
        self.assertTrue(result["telemetry"]["total_pipeline_latency_ms"] > 0)

    async def test_orchestrator_multi_turn_history(self):
        """Verify conversation continuity across multiple turns."""
        res1 = await orchestrator.handle_message(self.test_session, self.test_user, "My project name is OmniAgent")
        self.assertIn("response", res1)

        history = db.get_history(self.test_session)
        self.assertEqual(len(history), 2) # user + assistant

        res2 = await orchestrator.handle_message(self.test_session, self.test_user, "What is my project name?")
        self.assertIn("response", res2)

        history_after = db.get_history(self.test_session)
        self.assertEqual(len(history_after), 4)

    def test_web_api_endpoints(self):
        """Verify FastAPI endpoints serve status, chat, mode, and history with fresh sessions."""
        api_sess = f"api_test_{uuid.uuid4().hex[:8]}"

        # 1. Status
        st = self.client.get("/api/status")
        self.assertEqual(st.status_code, 200)
        self.assertEqual(st.json()["status"], "online")

        # 2. Chat (Default auto mode routes algorithm question to Qwen)
        c = self.client.post("/api/chat", json={
            "session_id": api_sess,
            "message": "Calculate the time complexity of quicksort algorithm",
            "mode": "auto"
        })
        self.assertEqual(c.status_code, 200)
        data = c.json()
        self.assertIn("response", data)
        self.assertEqual(data["agent_used"], "qwen")

        # 3. History
        h = self.client.get(f"/api/history?session_id={api_sess}")
        self.assertEqual(h.status_code, 200)
        self.assertTrue(len(h.json()["messages"]) >= 2)

        # 4. Mode Update
        m = self.client.post("/api/mode", json={"session_id": api_sess, "mode": "council"})
        self.assertEqual(m.status_code, 200)
        self.assertEqual(m.json()["mode"], "council")

if __name__ == "__main__":
    unittest.main()
