# OmniAgent: Unified Multi-Agent Collective

A production-ready, 24/7 cloud-accessible AI collective uniting **Claude 3.5 Sonnet**, **Gemini 2.5 Flash**, **GPT-4o**, **Qwen 2.5 72B**, and **Kimi k3** into a single cohesive agent system. Access it anytime on your phone while in college via **Telegram** or the **Mobile Web App**.

---

## 🏛️ Architecture: How Multiple Models Work as One Unit

```
                 [Your Phone: Telegram / Mobile Web UI]
                                   │
                                   ▼ (HTTPS / WSS)
                 ┌───────────────────────────────────┐
                 │    OmniAgent Cloud Orchestrator   │
                 │   • Session & Conversation Memory │
                 │   • Intelligent Task Router       │
                 └─────────────────┬─────────────────┘
                                   │
        ┌──────────────┬───────────┼───────────┬──────────────┐
        ▼              ▼           ▼           ▼              ▼
    [Claude 3.5]  [Gemini 2.5]  [GPT-4o]   [Qwen 2.5]    [Kimi k3]
    Architecture   Fast Search   Logic &    Algorithms    Long-Doc &
    & Reasoning   & Research     Actions    & Math Logic   Papers
        └──────────────┴───────────┬───────────┴──────────────┘
                                   │
                                   ▼
                 ┌───────────────────────────────────┐
                 │    Council Consensus Engine       │
                 │   • Parallel Execution (Async)    │
                 │   • Hallucination Cross-Check     │
                 │   • Unified Single Master Answer  │
                 └─────────────────┬─────────────────┘
                                   │
                                   ▼
                     [Delivered Cleanly to Phone]
```

### 1. The Three Operating Modes
* **Mode 1: Smart Auto-Router (`/mode auto`)**
  The supervisor analyzes your prompt and immediately routes it to the optimal specialist:
  * Coding & Algorithms $\rightarrow$ **Qwen 2.5 72B** (with Claude review)
  * System Design & Deep Reasoning $\rightarrow$ **Claude 3.5 Sonnet**
  * Factual Queries & Broad Research $\rightarrow$ **Gemini 2.5 Flash**
  * Operational Logic & Everyday Tasks $\rightarrow$ **GPT-4o**
  * Massive Contexts & Complex Literature $\rightarrow$ **Kimi k3**
* **Mode 2: The Multi-Agent Council (`/mode council` or prefix `council:`)**
  For critical choices, all 5 models run **in parallel**. The Synthesizer compares their reasoning, cross-checks facts to eliminate hallucinations, and delivers a unified master response with per-model insights.
* **Mode 3: Pinned Specialist (`/mode claude`, `/mode gemini`, etc.)**
  Locks conversation to a specific model when you want dedicated focus.

---

## 📱 5-Minute Setup: 24/7 Mobile Access from College

### Method A: Private Telegram Bot (Recommended)
You do not need to install custom apps; Telegram works reliably on campus Wi-Fi and mobile data with push notifications and code formatting.

1. **Create your Bot in 2 Minutes**:
   * Open Telegram on your phone and search for `@BotFather`.
   * Send `/newbot`, name your bot (e.g., `MyOmniAgentBot`), and give it a username ending in `bot`.
   * Copy the `HTTP API Token` provided by BotFather.
2. **Get your User ID** (Prevents anyone else from using your bot):
   * In Telegram, search `@userinfobot` and tap Start. It will reply with your numeric `Id` (e.g. `123456789`).
3. **Add to `.env`**:
   ```bash
   TELEGRAM_BOT_TOKEN="123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
   TELEGRAM_ALLOWED_USERS="123456789"
   ```
4. Start the server. Now you can chat with your multi-agent collective right from Telegram anywhere!

### Method B: Mobile Web Client
* Open `http://your-server-url:8000` in Safari or Chrome on your phone.
* Tap **Share $\rightarrow$ Add to Home Screen** to install it as an app icon.
* If protected with `SECRET_KEY`, tap the settings gear in the top right to store your PIN.

---

## 🔑 Model API Keys: Two Flexible Options

You can configure the system using either option in `.env`:

### Option 1 (Easiest): One Universal Key via OpenRouter
Instead of managing 5 separate billing accounts, create an account on [OpenRouter.ai](https://openrouter.ai/) and generate a single key. It gives access to Claude, Gemini, GPT-4o, Qwen 2.5, and Kimi:
```bash
OPENROUTER_API_KEY="sk-or-v1-..."
```

### Option 2: Direct Provider API Keys
Use individual keys from each model provider as you acquire them:
```bash
ANTHROPIC_API_KEY="sk-ant-..."      # Claude
GEMINI_API_KEY="AIzaSy..."          # Gemini (Google AI Studio - Free tier available)
OPENAI_API_KEY="sk-proj-..."        # OpenAI
DASHSCOPE_API_KEY="sk-..."          # Qwen (Alibaba DashScope)
MOONSHOT_API_KEY="sk-..."           # Kimi (Moonshot AI)
```
*Note: If no API keys are supplied initially, the system runs with an intelligent **Mock/Simulation Fallback** so you can test the entire routing, council, database, and Telegram flows without errors!*

---

## ☁️ 24/7 Free Cloud Hosting (Always Online)

### Option 1: Deploy to Render.com (1-Click, Free)
1. Fork or push this repository to GitHub.
2. Log into [Render.com](https://render.com/) and click **New + $\rightarrow$ Web Service**.
3. Select your repository. Render automatically reads `render.yaml`.
4. In the Render Environment Variables tab, paste your `TELEGRAM_BOT_TOKEN` and your AI keys.
5. Click **Deploy**. Your bot is now live on the internet 24 hours a day!

### Option 2: Docker Compose (VPS / Self-Hosted)
```bash
# 1. Clone repository
git clone <your-repo> && cd multi_agent_system

# 2. Configure environment
cp .env.example .env
nano .env

# 3. Start 24/7 background container
docker compose up -d

# 4. View logs
docker compose logs -f
```

---

## 🧪 Testing the Entire System Locally

Run the automated test suite verifying model adapters, router heuristics, council consensus, database, and REST APIs:

```bash
python3 -m unittest multi_agent_system/test_system.py
```

To run the local server:
```bash
python3 -m multi_agent_system.main
```
Navigate to `http://localhost:8000` in your browser.

---

## 💬 Command Reference Cheatsheet

| Telegram Command | Action |
| :--- | :--- |
| `/start` | Welcome overview & model collective roster |
| `/mode auto` | Smart router delegates tasks dynamically |
| `/mode council` | Queries Claude, Gemini, GPT, Qwen & Kimi simultaneously and synthesizes |
| `/mode [model]` | Pins one specific model (`claude`, `gemini`, `chatgpt`, `qwen`, `kimi`) |
| `/status` | Shows live telemetry, response latencies, and context memory count |
| `/clear` | Clears conversation memory for a fresh session |
| `/help` | Complete manual and usage tips |
