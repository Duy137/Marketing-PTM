# 🚀 PTM Marketing OS & Auto-Post Engine

> **Production-Grade Stateful Multi-Agent Marketing Automation Platform for B2B Manufacturing**  
> *Orchestrated with LangGraph • Human-in-the-Loop Telegram Control Plane • Dynamic Multi-Provider LLM Factory • Event-Driven Plugin Architecture*

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange.svg?logo=langchain&logoColor=white)](https://github.com/langchain-ai/langgraph)
[![FastAPI](https://img.shields.io/badge/Webhook-FastAPI%20%2F%20Uvicorn-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LLM Support](https://img.shields.io/badge/LLM-OpenAI%20%7C%20Gemini%20%7C%20Claude-purple.svg)](https://platform.openai.com/)
[![Telegram Bot API](https://img.shields.io/badge/Control%20Plane-Telegram%20Bot%20API-2CA5E0.svg?logo=telegram&logoColor=white)](https://core.telegram.org/bots/api)
[![Facebook Graph API](https://img.shields.io/badge/Social%20API-Meta%20Graph%20v19.0-1877F2.svg?logo=facebook&logoColor=white)](https://developers.facebook.com/docs/graph-api)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 Executive Summary

**PTM Marketing OS** is an end-to-end, agentic marketing automation system built for **PTM** (a leading B2B architectural stainless steel and interior materials manufacturer in Vietnam). 

Unlike trivial one-shot AI wrappers, this system solves real-world industrial marketing constraints:
1. **Low organic engagement in niche B2B**: High customer acquisition cost (CAC) requires disciplined, multi-angle brand storytelling across 5 distinct content modes (Product Showcase, Educational, Social Proof / Factory Dispatch, B2B Sales, and Seasonal Promos).
2. **Brand reputation & Hallucination risks**: Zero tolerance for inaccurate technical specs or false pricing. Requires a strict **Human-in-the-Loop (HITL)** approval gate before publishing.
3. **Multi-Channel & Multi-Page management**: Concurrent, atomic publishing to multiple targeted Facebook Fanpages with automated asset allocation.
4. **Cost vs. Quality Optimization**: Dynamic LLM routing dispatching high-reasoning models (GPT-4o / Claude 3.5 Sonnet) for copywriting while routing low-cost models (GPT-4o-mini / Gemini Flash) for image categorization and data analytics.

---

## 🏛️ System Architecture

The system is built on a **Stateful Directed Acyclic Graph (DAG)** with interactive cycles using **LangGraph**, decoupled from external I/O via a **FastAPI Webhook Server** and a lightweight **Event-Driven Hook Bus**.

```mermaid
flowchart TB
    subgraph INGRESS["🌐 Ingress & Control Plane"]
        TG["👤 User (CMO / Marketer)\nTelegram Mobile App"]
        CF["☁️ Cloudflare Tunnel\n(Zero Trust / Public Ingress)"]
        WH["⚡ FastAPI Webhook Server\n(<50ms response, async queue)"]
        TG <-->|Interactive UI / Keyboards| CF <-->|Webhooks| WH
    end

    subgraph PREPIPE["🧭 Phase 1: Pre-Pipeline (Zero LLM Cost)"]
        TS["🕹️ Topic Selector Controller"]
        CSV[("📁 data/topics.csv\n99 Topics + State Tracking")]
        WH <-->|Non-blocking IPC| TS <-->|CRUD / Pagination| CSV
    end

    subgraph GRAPH["🤖 Phase 2: LangGraph Stateful Pipeline"]
        direction TB
        N1["1️⃣ topic_picker\n(Load state & metadata)"]
        N2["2️⃣ content_writer\n(LLM + Brand Voice + Persona)"]
        N3["3️⃣ image_picker\n(Semantic asset allocation)"]
        N4["4️⃣ approver\n(Telegram Preview + HITL Actions)"]
        N5["5️⃣ page_selector\n(Multi-page checklist)"]
        N6["6️⃣ publisher\n(Facebook Graph API v19.0)"]

        N1 --> N2 --> N3 --> N4
        N4 -->|✅ Approved| N5 --> N6 --> END1(["🏁 Done / Main Menu"])
        N4 -->|🔄 Same Topic| N2
        N4 -->|⬅️ Change Topic / ❌ Reject / ⏰ Timeout| END2(["🏠 Return to Main Menu"])
    end

    subgraph HOOKS["🔌 Event-Driven Plugin Bus (shared/hooks.py)"]
        BUS{"⚡ Event Bus\nfire(event, payload)"}
        P1["📊 Plugin: fb_insights\n(Logs post metadata & joins Graph API metrics)"]
        P2["📰 Plugin: rss_reader\n(Fetches Real Estate / B2B News digest)"]
        
        BUS -->|on_post_published| P1
        BUS -->|on_report_requested| P1
        BUS -->|on_session_start| P2
    end

    TS -->|Trigger Graph Execution| N1
    N6 -.->|fire('on_post_published')| BUS
    WH -.->|fire('on_report_requested')| BUS
```

---

## 💡 Key Engineering Highlights

### 1. Dynamic LLM Factory with Per-Task Profiling (`shared/llm_factory.py`)
Avoids hardcoding vendor APIs across agents. Implements a centralized **Factory Pattern** driven by environment variables:
- **Tier 1 (High Reasoning / Creative)**: `content_writer` uses `gpt-4o` (or `gemini-1.5-pro` / `claude-3-5-sonnet`) with calibrated temperature (`0.7`) for brand voice compliance and nuanced Vietnamese copywriting.
- **Tier 2 (Classification / Extraction)**: `image_picker` and `fb_insights` use `gpt-4o-mini` (or `gemini-1.5-flash`) at temperature `0.1` for deterministic JSON / tag extraction.
- **Cost Reduction**: Achieves ~**72% cost savings** compared to running all agents on flagship models.

```python
# Clean developer ergonomics
from shared.llm_factory import create_llm_for_task

llm_writer = create_llm_for_task("content_writer")  # Routes to Tier 1
llm_picker = create_llm_for_task("image_picker")    # Routes to Tier 2
```

---

### 2. Human-in-the-Loop (HITL) Telegram Control Plane
Rather than running in an unmonitored cron black box, the engine treats Telegram as a **remote administrative control plane**:
- **Zero-Latency Ingress**: FastAPI webhook responds with `200 OK` in `<50ms` while offloading callback processing to a thread-safe IPC queue (`api/pending_store.py`).
- **Interactive Lifecycle**:
  - **Review & Approve (`[✅ Duyệt đăng]`)**: Advances LangGraph state to multi-page dispatch.
  - **In-place Regeneration (`[🔄 Cùng chủ đề]`)**: Cycles back to `content_writer` node with fresh seed.
  - **Live Photo Injection (`[🖼️ Gửi ảnh]`)**: Allows the marketer to take real factory photos on their phone and upload them into the Telegram chat; the bot receives the raw byte streams into RAM and overrides local disk stock photos on the fly without disk pollution.

---

### 3. Decoupled Event Hook & Plugin Architecture (`shared/hooks.py`)
Inspired by WordPress/Django signal architectures, the core pipeline emits lifecycle events (`on_session_start`, `on_post_published`, `on_report_requested`):
- **Zero Core Mutation**: New features (like RSS aggregators, Slack alerts, or CRM webhooks) are added as isolated plugins in `plugins/<plugin_name>/` without touching `main.py` or the LangGraph pipeline.
- **Facebook Insights Join Loop**: `fb_insights` intercepts `on_post_published` to record `facebook_post_id`, `topic_id`, `mode`, and `image_types` into `logs/post_log.csv`. When the user requests a performance report on Telegram, it fetches Facebook Graph API v19.0 metrics (`post_impressions_unique`, `post_engaged_users`, `post_clicks`), performs an in-memory **relational JOIN**, and passes the dataset to an LLM to generate strategic executive insights.

---

### 4. Resilient Multi-Threading & Windows Session Loop
- **Infinite Graceful Session**: Persistent `while True` main loop supporting repeated operations without restarting the process.
- **Cross-Platform Signal Handling**: Fixed blocking timeout quirks on Windows environments via non-blocking `queue.get(timeout=1.0)` polling, enabling clean `Ctrl+C` interrupt and background tunnel teardown.
- **Concurrent Fanpage Publishing**: Multi-page uploads executed concurrently via `concurrent.futures.ThreadPoolExecutor` with per-page error isolation.

---

## 📂 Project Structure

```
ptm_auto_post/
├── main.py                     # Entry point & LangGraph StateGraph assembler
├── config/
│   ├── settings.py             # Strongly-typed environment & path validator
│   └── .env                    # Secrets & API credentials (excluded from git)
├── shared/
│   ├── llm_factory.py          # Centralized LLM factory with per-task routing
│   └── hooks.py                # Event-driven Hook Bus (on / fire)
├── agents/                     # LangGraph Pipeline & State Nodes
│   ├── state.py                # TypedDict PostState definition
│   ├── topic_selector.py       # Phase 1: Pre-pipeline Telegram UI controller
│   ├── topic_picker.py         # Phase 2 - Node 1: State initialization
│   ├── content_writer.py       # Phase 2 - Node 2: LLM content generation
│   ├── image_picker.py         # Phase 2 - Node 3: Semantic image selection
│   ├── approver.py             # Phase 2 - Node 4: Telegram HITL review gate
│   ├── page_selector.py        # Phase 2 - Node 5: Multi-page selection
│   └── publisher.py            # Phase 2 - Node 6: Facebook Graph API dispatcher
├── plugins/                    # Modular Extensibility Layer
│   ├── __init__.py             # Active plugin registry (toggle via imports)
│   ├── fb_insights/            # Analytics logging + Graph API JOIN + LLM digest
│   └── rss_reader/             # Industry news ingestion (Cafef BĐS, VnExpress)
├── services/                   # Stateless I/O & API Wrappers
│   ├── telegram_service.py     # Telegram Bot API wrapper (HTML formatting, keyboards)
│   ├── topic_service.py        # CSV database engine (Pagination, state toggle)
│   └── post_log_service.py     # Analytics logger & CSV parser
├── views/
│   └── telegram_views.py       # Presentation layer for Telegram HTML templates
├── api/
│   ├── webhook_server.py       # Lightweight FastAPI webhook ingress
│   └── pending_store.py        # Thread-safe callback registry & event queue
├── knowledge/                  # RAG / Prompt Domain Knowledge
│   ├── company.md              # PTM company background & UVP
│   ├── products.md             # Inox 304/201 technical specifications
│   ├── personas.md             # B2B Contractor & Architect personas
│   ├── brand_voice.md          # Tone, rules & forbidden jargon
│   └── content_modes.md        # 5 strategic content frameworks
├── data/
│   └── topics.csv              # Topic repository (99 topics with status flags)
├── media/                      # Organized product media folders
└── logs/                       # Execution logs & analytics history
```

---

## ⚙️ Tech Stack & Dependencies

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Orchestration** | `LangGraph`, `LangChain Core` | Stateful multi-step graph with cyclic routing |
| **LLM Providers** | `OpenAI GPT-4o`, `Google Gemini 1.5/2.0`, `Anthropic Claude` | Multi-vendor fallback & per-task model routing |
| **API & Webhook** | `FastAPI`, `Uvicorn` | High-throughput asynchronous webhook ingress |
| **Ingress Tunnel** | `Cloudflare Tunnel (cloudflared)` | Secure public webhook URL without public IP exposure |
| **External APIs** | `Meta Facebook Graph API v19.0`, `Telegram Bot API` | Multi-page publishing & interactive HITL interface |
| **Data & RSS** | `pandas`, `feedparser`, `requests` | CSV data persistence & external industry news syndication |

---

## 🛠️ Getting Started

### 1. Prerequisites
- **Python**: `3.11` or higher
- **Cloudflare Tunnel (`cloudflared`)**: Downloaded and placed in root directory or added to `PATH`
- **Telegram Bot**: Bot token created via [@BotFather](https://t.me/botfather)
- **Facebook Graph API**: Page Access Tokens with `pages_manage_posts` & `pages_read_engagement` permissions

### 2. Installation
```bash
# Clone repository
git clone https://github.com/your-username/ptm-marketing-os.git
cd ptm-marketing-os

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration (`config/.env`)
Create `config/.env` using the following schema:

```ini
# --- Telegram Bot Configuration ---
TELEGRAM_BOT_TOKEN="123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
TELEGRAM_CHAT_ID="987654321"

# --- LLM API Keys ---
OPENAI_API_KEY="sk-proj-..."
GEMINI_API_KEY="AIzaSy..."
ANTHROPIC_API_KEY="sk-ant-..."

# --- Task-Based LLM Model Configuration ---
LLM_PROVIDER="openai"
LLM_MODEL="gpt-4o"

LLM_CONTENT_WRITER_PROVIDER="openai"
LLM_CONTENT_WRITER_MODEL="gpt-4o"
LLM_CONTENT_WRITER_TEMP=0.7

LLM_IMAGE_PICKER_PROVIDER="openai"
LLM_IMAGE_PICKER_MODEL="gpt-4o-mini"
LLM_IMAGE_PICKER_TEMP=0.1

# --- Facebook Fanpages Configuration ---
FACEBOOK_PAGE_1_ID="100000000000001"
FACEBOOK_PAGE_1_NAME="PTM - Nẹp Nhôm Nẹp Inox Cao Cấp"
FACEBOOK_PAGE_1_TOKEN="EAA..."

FACEBOOK_PAGE_2_ID="100000000000002"
FACEBOOK_PAGE_2_NAME="Gia Công Inox PVD PTM"
FACEBOOK_PAGE_2_TOKEN="EAA..."
```

### 4. Running the Engine
```bash
python main.py
```
Upon startup, the engine will:
1. Initialize the **Cloudflare Tunnel** and expose FastAPI on an ephemeral `https://*.trycloudflare.com` URL.
2. Register the webhook with Telegram API automatically.
3. Fire `on_session_start` plugins (e.g. RSS reader digest).
4. Render the interactive **Main Menu** to the authorized Telegram Chat.

---

## 🎯 Production Telegram Workflow

```
[Main Menu] ──────────────────────────────────────────────────────────
  ├── ✍️ Viết bài (Start content flow)
  └── 📊 Báo cáo (On-demand Facebook Insights & AI post-mortem)

[Topic Picker Screen] ────────────────────────────────────────────────
  ├── [✅ Viết bài này]   ──> Trigger LangGraph Pipeline
  ├── [🔄 Gợi ý khác]    ──> Rotate next prioritized topic
  └── [📋 Xem danh sách] ──> Paginated interactive table (Toggle ⬜/✅/⏸)

[Review & Approval Screen] ───────────────────────────────────────────
  ├── [✅ Duyệt đăng]     ──> Open Fanpage selection modal ──> Publish
  ├── [🔄 Cùng chủ đề]   ──> Re-invoke Content Writer with fresh angle
  ├── [⬅️ Chọn lại topic]──> Return to Topic Selector
  ├── [🖼️ Gửi ảnh]       ──> Enter custom image upload mode
  └── [❌ Bỏ qua]         ──> Cancel run & return to Main Menu
```

---

## 🧠 Strategic Knowledge Base (RAG & Persona Injection)

The AI writer is grounded in curated markdown domain documents inside `knowledge/`:
- **5 Strategic Modes**:
  - `Product`: Technical specs, V/U/T profile dimensions, PVD vacuum plating durability.
  - `Educational`: Installation techniques, 304 vs 201 corrosion comparisons.
  - `Social Proof`: Real-world project deliveries, bulk packing for contractors.
  - `B2B Sales`: Factory direct pricing, custom CNC bending & laser cutting capabilities.
  - `Seasonal`: Year-end project completion urgencies.
- **Guardrails**: Strict prohibition of generic consumer phrasing ("cho gia đình bạn"); strictly enforces B2B tone tailored for interior contractors, architects, and site engineers.

---

## 🗺️ Architectural Roadmap: Evolution to Autonomous Marketing OS

The system is architected for seamless evolution into a fully autonomous marketing operating system:

| Phase | State | Key Capabilities | Status |
| :--- | :--- | :--- | :--- |
| **Phase 1: Foundation** | Current | LangGraph pipeline, HITL Telegram control plane, LLM Factory, Plugin Bus, Multi-page posting | 🟢 **Production Ready** |
| **Phase 2: Intelligence Loop** | In Progress | **Trend Analyst Agent** (Google Ads search query mining), **Topic Strategist** (auto weekly schedule), **Performance Analyst** (multi-day attribution) | 🟡 **Iterating** |
| **Phase 3: Multi-Agent Scale** | Planned | **Competitor Gap Agent**, **Automated Content QA Agent**, multi-channel distribution (Website SEO + Video Scripting) | ⚪ **Planned** |

---

## 👨‍💻 Engineering Decisions & Trade-offs Log

- **Why LangGraph over linear LangChain Chains?**  
  *Decision*: Linear chains cannot model cyclic HITL feedback loops (e.g., user asks to rewrite with same topic, or switches topics midway). LangGraph's state machine provides type-safe state mutations and deterministic checkpointing.
- **Why Event Hooks over Monolithic Controllers?**  
  *Decision*: Decouples high-frequency analytics and peripheral features (RSS, Insights) from the critical posting path, eliminating regression risks when adding new capabilities.
- **Why HITL Telegram UI instead of full autonomy?**  
  *Decision*: In B2B manufacturing, brand trust is paramount. An incorrect technical tolerance or faulty alloy guarantee can cause immediate commercial liability. A 30-second mobile review gate ensures 100% brand safety.

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
