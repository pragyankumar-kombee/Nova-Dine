# Nova Dine — AI Inventory Assistant

> AI-powered restaurant inventory management built for Kombee Hackathon 2.0.
> Predict demand, reduce waste, and streamline kitchen operations using Groq LLMs, RAG, and a Flask web interface.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Setup & Installation](#setup--installation)
5. [Environment Variables](#environment-variables)
6. [Running the App](#running-the-app)
7. [Terminal CLI (run.py)](#terminal-cli-runpy)
8. [Architecture & Flow](#architecture--flow)
9. [AI Backbone](#ai-backbone)
10. [Web Pages](#web-pages)
11. [API Reference](#api-reference)
12. [Database Models](#database-models)
13. [RAG System](#rag-system)
14. [Output Files](#output-files)

---

## Project Overview

Nova Dine is a full-stack AI assistant for restaurant inventory management. It combines:

- A **Flask web app** with 15 pages (dashboard, inventory, chat, analytics, etc.)
- An **AI backbone** that classifies queries, routes them to the right Groq model, and validates responses
- A **terminal CLI** (`run.py`) for generating ingredient order lists with PDF and Word export
- A **RAG pipeline** using ChromaDB + HuggingFace embeddings for menu-aware context
- A **PostgreSQL database** for inventory, orders, menus, and AI insights

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web Framework | Flask + Flask-SQLAlchemy + Flask-CORS |
| LLM | Groq — `llama-3.3-70b-versatile`, `llama-3.1-8b-instant` |
| Embeddings | HuggingFace `all-MiniLM-L6-v2` |
| Vector Store | ChromaDB |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| PDF Export | fpdf2 |
| Word Export | python-docx |
| Frontend | HTML + Bootstrap 5 + Chart.js + FontAwesome |
| Config | pydantic-settings + python-dotenv |

---

## Project Structure

```
nova-dine/
│
├── main_app.py              # Flask app entry point — all routes & API endpoints
├── run.py                   # Terminal CLI — interactive ingredient order generator
├── app.py                   # Alternate/legacy entry point
├── seed_hackathon.py        # Seeds PostgreSQL with sample data
├── process_and_save.py      # Batch menu processing utility
├── requirements.txt
├── .env                     # Environment variables (not committed)
│
├── backbone/                # AI orchestration layer
│   ├── orchestrator.py      # Main pipeline: classify → route → validate
│   ├── classifier.py        # Query classification (REASONING/RAG/ANALYTICS etc.)
│   ├── router.py            # Model selection, caching, cost tracking
│   ├── validators.py        # Response safety & relevance validation
│   ├── observability.py     # Token/cost/latency logging
│   └── self_heal.py         # Auto-retry and fallback logic
│
├── config/
│   └── settings.py          # Pydantic settings — loads from .env
│
├── database/
│   ├── models.py            # SQLAlchemy models (legacy/Mongo-style)
│   ├── init_db.py           # Creates tables
│   ├── verify_db.py         # Checks DB connection
│   └── debug_db.py          # Debug utilities
│
├── rag/
│   ├── ingestion.py         # Chunks and embeds menu text into ChromaDB
│   ├── retriever.py         # Similarity search over stored embeddings
│   └── vector_store.py      # ChromaDB client wrapper
│
├── templates/               # Jinja2 HTML templates (15 pages)
│   ├── index.html
│   ├── dashboard.html
│   ├── inventory.html
│   ├── menu_upload.html
│   ├── chat.html
│   ├── analytics.html
│   ├── orders.html
│   ├── reports.html
│   ├── recipes.html
│   ├── suppliers.html
│   ├── waste_management.html
│   ├── staff.html
│   ├── settings.html
│   ├── help.html
│   └── test.html
│
├── static/
│   ├── css/style.css        # Unified styles — header, footer, components
│   └── js/main.js           # Shared JS — nav, dropdowns, mobile menu
│
├── docs/
│   └── architecture.md      # System architecture notes
│
├── vector_db/               # ChromaDB persistent storage
├── vector_store/            # Alternate ChromaDB path
└── uploads/                 # Uploaded menu files (PDF/TXT)
```

---

## Setup & Installation

### Prerequisites

- Python 3.9+
- PostgreSQL running locally (default port 5432)
- Git

### 1. Clone the repo

```bash
git clone https://github.com/pragyankumar-kombee/Nova-Dine.git
cd nova-dine
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up PostgreSQL

Create the database:

```sql
CREATE DATABASE kombee_hackathon;
```

Then seed it with sample data:

```bash
python seed_hackathon.py
```

Or initialise empty tables:

```bash
python database/init_db.py
```

### 5. Configure environment variables

Copy the example and fill in your keys:

```bash
cp .env.example .env
```

See [Environment Variables](#environment-variables) below.

---

## Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://postgres:admin123@localhost:5432/kombee_hackathon

# API Keys
GROQ_API_KEY=your_groq_api_key_here
HUGGINGFACE_API_KEY=your_hf_token_here
GEMINI_API_KEY=your_gemini_key_here        # optional

# Flask
SECRET_KEY=your_secret_key_here
FLASK_APP=main_app.py
FLASK_DEBUG=True
PORT=5000
```

Get your free Groq API key at [console.groq.com](https://console.groq.com).
Get your HuggingFace token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).

---

## Running the App

### Web server

```bash
python main_app.py
```

Then open [http://localhost:5000](http://localhost:5000).

Or with Flask CLI:

```bash
flask --app main_app run --debug
```

### Verify database connection

```bash
python test_conn.py
```

---

## Terminal CLI (run.py)

The CLI lets you generate a full ingredient order list for any dish without opening a browser.

```bash
python run.py
```

You will be prompted for:

1. Dish name (e.g. `paneer korma`)
2. Restaurant name
3. Current stock — enter one item per line as `ingredient, quantity`, blank line to finish

**Example session:**

```
  Dish name        : paneer korma
  Restaurant name  : Indian Spice Restaurant

  Current stock  →  ingredient, quantity  (blank to finish)
  › tomatoes, 50g
  › paneer, 200g
  › onion, 100g
  › cream, 500ml
  ›
```

**Output:**

- Colour-coded terminal table with CRITICAL / HIGH / MEDIUM priority sections
- Full recipe steps
- `paneer_korma_order_list.pdf` — styled PDF with colour-coded sections
- `paneer_korma_order_list.docx` — Word document with tables and recipe

Both files are saved in the project root.

---

## Architecture & Flow

### Web request flow

```
Browser Request
      │
      ▼
Flask Route (main_app.py)
      │
      ├── Static pages → render_template()
      │
      └── API endpoints (/api/*)
            │
            ├── /api/menu/upload    → ai_extract_dishes() → PostgreSQL + ChromaDB
            ├── /api/chat/query     → ai_classify_query() → generate_predictions()
            ├── /api/inventory/*    → SQLAlchemy queries → JSON response
            └── /api/observability  → AIInsight table → metrics
```

### Terminal CLI flow (run.py)

```
User Input (dish + stock)
      │
      ▼
AIOrchestrator.process()
      │
      ├── EnhancedClassifier.classify()   → use_case, complexity, model suggestion
      │
      ├── _build_prompt()                 → structured prompt with stock context
      │
      ├── AdvancedRouter.route()          → selects Groq model, checks cache
      │         │
      │         └── ChatGroq.ainvoke()    → LLM response (JSON)
      │
      └── ResponseValidator.validate()    → safety + relevance checks
            │
            ▼
      parse_response()                    → extract JSON from LLM output
            │
            ▼
      print_order_list()                  → terminal output
      save_pdf()                          → fpdf2 PDF
      save_word()                         → python-docx Word file
```

---

## AI Backbone

Located in `backbone/`, this layer handles all LLM interactions.

### Classifier (`backbone/classifier.py`)

Classifies every query into one of:

| Use Case | Description |
|---|---|
| `REASONING` | Complex multi-step questions |
| `CODING` | Code generation or debugging |
| `RAG` | Menu/ingredient context lookups |
| `LIGHTWEIGHT` | Simple factual queries |
| `MULTI_TURN` | Conversational follow-ups |
| `ANALYTICS` | Data analysis and forecasting |

Also returns: complexity score (0–1), whether context is needed, suggested model, estimated tokens.

### Router (`backbone/router.py`)

- Selects the right Groq model based on classification
- Checks in-memory cache (MD5 hash of prompt + model) before calling the API
- Tracks cost per token, total spend, cache hits, model usage
- Retries up to 3 times with exponential backoff on failure
- Falls back to `llama-3.1-8b-instant` on error

**Active models (non-deprecated):**

| Model | Use |
|---|---|
| `llama-3.3-70b-versatile` | Reasoning, complex queries |
| `llama-3.1-8b-instant` | Lightweight, fast responses |

### Validator (`backbone/validators.py`)

Runs 5 checks on every LLM response:

1. Content safety — blocks harmful patterns
2. Relevance — checks for inventory/food domain keywords (RAG queries)
3. Length — flags responses under 5 words or over 1000 words
4. Structure — validates table formatting
5. Hallucination check — secondary LLM verification if score drops below 0.7

Returns a score (0–1) and a corrected response.

### Orchestrator (`backbone/orchestrator.py`)

Ties the full pipeline together:

```python
result = await orchestrator.process(query, context)
```

Returns: response text, use_case, model_used, cached, cost, time_taken, tokens_used, validation_score.

---

## Web Pages

All pages share a unified header (sticky, with dropdown nav) and footer (4-column grid with social links and system status).

| Route | Template | Description |
|---|---|---|
| `/` | `index.html` | Landing page with AI metrics |
| `/dashboard` | `dashboard.html` | Stock overview, charts, AI alerts |
| `/inventory` | `inventory.html` | Full inventory table with filters |
| `/menu-upload` | `menu_upload.html` | PDF/TXT menu upload + AI extraction |
| `/chat` | `chat.html` | AI chat interface |
| `/analytics` | `analytics.html` | Demand forecasting charts |
| `/orders` | `orders.html` | Order history |
| `/reports` | `reports.html` | Inventory value reports |
| `/recipes` | `recipes.html` | Recipe optimiser |
| `/suppliers` | `suppliers.html` | Supplier management |
| `/waste-management` | `waste_management.html` | Waste tracking |
| `/staff` | `staff.html` | Staff performance |
| `/settings` | `settings.html` | App configuration |
| `/help` | `help.html` | Help centre |
| `/test` | `test.html` | Backbone observability logs |

---

## API Reference

### Menu

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/menu/upload` | Upload PDF/TXT menu, extract dishes via AI |
| `GET` | `/api/menu/latest?user_id=1` | Get latest processed menu for a user |

### Inventory

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/inventory/stock` | All products with stock levels |
| `GET` | `/api/inventory/low-stock` | Items below reorder level |
| `POST` | `/api/inventory/cart/generate` | Generate order cart from ingredient list |

### Chat

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat/query` | Send a query, get AI response + predictions |

### Analytics & Reports

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/analytics/demand-forecast?days=30` | 30-day demand forecast per product |
| `GET` | `/api/reports/inventory-value` | Inventory value by category |
| `GET` | `/api/orders/history?days=30` | Order history summary |
| `GET` | `/api/observability/logs` | AI query logs with token/cost metrics |

### Other

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health check |
| `GET` | `/api/test-db` | Database connection test |
| `POST` | `/api/waste/track` | Log waste entry |
| `GET` | `/api/staff/performance` | Staff metrics |
| `POST` | `/api/recipes/optimize` | Check if a recipe can be made with current stock |

---

## Database Models

Defined in `main_app.py` (SQLAlchemy) and `database/models.py` (Pydantic/legacy):

| Model | Table | Key Fields |
|---|---|---|
| `User` | `users` | id, username, email, restaurant_name |
| `Product` | `products` | id, name, category, unit, current_stock, reorder_level, supplier |
| `Order` | `orders` | id, user_id, order_date, total_amount |
| `OrderDetail` | `order_details` | id, order_id, product_id, quantity |
| `MenuDocument` | `menu_documents` | id, user_id, filename, content, processed_data (JSON) |
| `AIInsight` | `ai_insights` | id, query, classification, response_json, created_at |

---

## RAG System

Located in `rag/`:

- `ingestion.py` — splits menu text into 500-char chunks with 50-char overlap, generates embeddings using `all-MiniLM-L6-v2`, stores in ChromaDB
- `retriever.py` — similarity search over stored chunks, returns top-k results with scores
- `vector_store.py` — ChromaDB client, persists to `./vector_db`

The vector store is used in the chat endpoint to inject relevant menu context into LLM prompts before answering inventory questions.

---

## Output Files

When using `run.py`, two files are generated in the project root:

### PDF (`<dish>_order_list.pdf`)

- Dark header bar with dish name
- Meta row (date + restaurant)
- Colour-coded sections: red (CRITICAL), amber (HIGH), indigo (MEDIUM)
- Per-ingredient table: required, current stock, order qty, supplier, cost, note
- Totals bar
- Green recipe section with step-by-step instructions

### Word (`<dish>_order_list.docx`)

- Same structure as PDF
- Proper Word headings (H1/H2/H3) for easy editing
- Alternating row shading in ingredient tables
- Numbered recipe list
- Colour-coded section headings matching priority level

---

## Notes

- Groq models `llama3-8b-8192`, `mixtral-8x7b-32768`, and `gemma-7b-it` are **decommissioned**. The project uses `llama-3.3-70b-versatile` and `llama-3.1-8b-instant` instead.
- MongoDB references in `database/models.py` are legacy — the active database is PostgreSQL via SQLAlchemy.
- The `backbone/` folder contains an async pipeline used by `run.py`. The web app (`main_app.py`) uses its own synchronous AI functions directly.
- ChromaDB telemetry is disabled via `ANONYMIZED_TELEMETRY=False`.
 ## PPT / VIDEO

[https://docs.google.com/presentation/d/1MeMuwfaMzgRw_mUjUUATSbX-KrdK56T6A3Mpw9QuW](https://docs.google.com/presentation/d/1MeMuwfaMzgRw_mUjUUATSbX-KrdK56T6A3Mpw9QuWTo/edit?usp=sharing)

https://www.kapwing.com/videos/69b8ed8f10199b0e50892ee8

