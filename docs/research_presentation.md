# Nova-Dine: An AI-Driven Restaurant Inventory Intelligence System

**Research Presentation — Technical Deep Dive**

---

## Abstract

Restaurant inventory management is a persistent operational challenge in the food service industry. Manual stock tracking, reactive ordering, and disconnected supplier workflows lead to food waste, stockouts, and revenue loss. Nova-Dine addresses this by combining a multi-stage LLM orchestration pipeline, Retrieval-Augmented Generation (RAG) over menu documents, and a structured priority-based output system — all served through both a web interface and a terminal CLI. This paper presents the system architecture, AI backbone design, prompt engineering strategy, and the rationale behind key technical decisions.

---

## 1. Problem Statement

Traditional restaurant inventory systems are:

- **Reactive** — orders are placed only after stockouts occur
- **Disconnected** — menu data, stock levels, and supplier info live in separate silos
- **Manual** — chefs and managers estimate ingredient needs from experience, not data
- **Unstructured** — no priority classification for what needs ordering urgently vs. this week

Nova-Dine proposes an AI-native solution where a natural language query ("make paneer korma for 50 covers") triggers a full pipeline that classifies intent, retrieves menu context, routes to the appropriate LLM, validates the output, and returns a structured, prioritized ingredient order list — exportable as PDF and Word.

---

## 2. System Architecture

```
User Input (Web / Terminal CLI)
         │
         ▼
┌─────────────────────────────────────────────────────┐
│                  Flask Application Layer             │
│  main_app.py — Routes, API endpoints, DB sessions   │
└──────────────────────┬──────────────────────────────┘
                       │
         ┌─────────────▼──────────────┐
         │      AI Backbone           │
         │  backbone/orchestrator.py  │
         │                            │
         │  1. EnhancedClassifier     │
         │  2. AdvancedRouter         │
         │  3. ResponseValidator      │
         └─────────────┬──────────────┘
                       │
         ┌─────────────▼──────────────┐
         │      LLM Layer (Groq)      │
         │  llama-3.3-70b-versatile   │
         │  llama-3.1-8b-instant      │
         └─────────────┬──────────────┘
                       │
         ┌─────────────▼──────────────┐
         │      RAG Layer             │
         │  ChromaDB vector store     │
         │  HuggingFace Embeddings    │
         │  (all-MiniLM-L6-v2)        │
         └─────────────┬──────────────┘
                       │
         ┌─────────────▼──────────────┐
         │      Database Layer        │
         │  PostgreSQL + SQLAlchemy   │
         │  Users, Products, Orders,  │
         │  MenuDocuments, AIInsights │
         └────────────────────────────┘
```

The system has four distinct layers: the Flask web/API layer, the AI backbone orchestration layer, the LLM inference layer (Groq API), and the persistence layer (PostgreSQL + ChromaDB).

---

## 3. File Structure and Responsibilities

```
nova-dine/
├── main_app.py              # Flask app, all routes, inline DB models, AI logic
├── run.py                   # Terminal CLI — standalone async runner
├── app.py                   # Alternate entry point
│
├── backbone/                # AI orchestration layer
│   ├── orchestrator.py      # Core pipeline: classify → route → validate
│   ├── classifier.py        # Intent classification (EnhancedClassifier)
│   ├── router/
│   │   └── model_router.py  # Dynamic model selection (AdvancedRouter)
│   ├── validators/
│   │   ├── json_validator.py
│   │   ├── hallucination_detector.py
│   │   └── code_linter.py
│   ├── engines/
│   │   ├── complexity_engine.py   # Query complexity scoring
│   │   ├── context_builder.py     # Prompt context assembly
│   │   └── cost_engine.py         # Token cost tracking
│   ├── models/
│   │   ├── groq_model.py          # Groq API wrapper
│   │   ├── reasoning_model.py     # Heavy model (70b)
│   │   └── lightweight_model.py   # Fast model (8b)
│   ├── observability.py     # Logging, metrics, AIInsight writes
│   └── self_heal.py         # Retry and fallback logic
│
├── rag/
│   ├── ingestion.py         # PDF parsing, chunking, embedding
│   ├── retriever.py         # Similarity search over ChromaDB
│   └── vector_store.py      # ChromaDB client wrapper
│
├── database/
│   ├── models.py            # SQLAlchemy ORM models
│   ├── init_db.py           # Schema creation
│   ├── seed/generate_data.py
│   └── verify_db.py
│
├── config/
│   ├── settings.py          # Pydantic BaseSettings — env var management
│   └── prompts/             # Externalized prompt templates
│       ├── classifier_prompt.txt
│       └── ingredient_extractor_prompt.txt
│
├── templates/               # 15 Jinja2 HTML templates
├── static/                  # CSS (style.css) + JS (main.js)
└── vector_db/ vector_store/ # ChromaDB persistence directories
```

**Key design decision:** `main_app.py` contains both the Flask routes and the inline AI logic (dish extraction, classification, response generation). The `backbone/` directory provides a more modular, async-capable version of the same pipeline used by `run.py`. This dual-path design allows the web app to run synchronously (Flask's default) while the terminal CLI uses Python's `asyncio` for non-blocking LLM calls.

---

## 4. AI Backbone — Deep Dive

### 4.1 The Orchestration Pipeline

The core of Nova-Dine is a three-stage pipeline defined in `backbone/orchestrator.py`:

```python
async def process(self, query: str, context: dict = None) -> dict:
    classification = await self.classifier.classify(query)   # Stage 1
    prompt = self._build_prompt(query, context)               # Stage 2
    result = await self.router.route(classification, prompt)  # Stage 3
    validation = await self.validator.validate(result["response"], classification.use_case)
    return { ...structured output... }
```

This is a **sequential multi-agent pattern** where each stage has a single responsibility:

| Stage | Component | Responsibility |
|---|---|---|
| 1 | `EnhancedClassifier` | Determine query intent and complexity |
| 2 | `_build_prompt()` | Assemble context-aware structured prompt |
| 3 | `AdvancedRouter` | Select model and execute inference |
| 4 | `ResponseValidator` | Score, correct, and flag the LLM output |

### 4.2 Intent Classification

The classifier maps free-text queries to one of five intent categories:

- `MENU` — questions about dishes, ingredients, recipes
- `INVENTORY` — stock level queries
- `PREDICTION` — demand forecasting requests
- `ORDER` — purchase order generation
- `GENERAL` — catch-all for unstructured queries

In `main_app.py`, this is implemented as a direct Groq call:

```python
def ai_classify_query(query):
    prompt = f"Classify intent: MENU, INVENTORY, PREDICTION, ORDER, or GENERAL. Query: '{query}'. Return ONLY the category word."
    res = groq_llm.invoke([HumanMessage(content=prompt)]).content.strip().upper()
```

The classifier uses `llama-3.3-70b-versatile` for accuracy. The response is a single word — this is intentional: single-token classification is fast, cheap, and easy to validate.

### 4.3 Dynamic Model Routing

Nova-Dine uses two Groq-hosted models with different cost/capability tradeoffs:

| Model | Use Case | Latency | Token Cost |
|---|---|---|---|
| `llama-3.3-70b-versatile` | Complex reasoning, structured JSON generation, recipe creation | ~2-4s | Higher |
| `llama-3.1-8b-instant` | Simple classification, quick lookups, fallback | ~0.5-1s | Lower |

The routing logic (in `AdvancedRouter`) selects the model based on the classification result and a complexity score. `INVENTORY` and `PREDICTION` queries that only need tabular data can use the 8b model. `ORDER` and `MENU` queries that require structured multi-field JSON with recipe steps use the 70b model.

**Why Groq?** Groq's LPU (Language Processing Unit) hardware delivers significantly lower inference latency than GPU-based providers for the same model size. For a real-time restaurant tool, sub-2-second response times are critical.

### 4.4 Prompt Engineering

The most critical prompt in the system is `_build_prompt()` in `orchestrator.py`. It enforces structured JSON output with a strict schema:

```python
return f"""You are an expert restaurant inventory assistant...

Return your response in this EXACT JSON format (no extra text, just valid JSON):
{{
  "ingredients": [
    {{
      "name": "...",
      "required": "350g",
      "current_stock": "50g",
      "order_quantity": "300g",
      "supplier": "...",
      "cost_inr": 60,
      "priority": "CRITICAL|HIGH|MEDIUM",
      "note": "..."
    }}
  ],
  "recipe_steps": ["Step 1: ...", ...],
  "total_cost_inr": 395
}}

Rules:
- CRITICAL = stock will run out within 1 day or is completely out
- HIGH = stock will last 2-3 more servings
- MEDIUM = stock is low but sufficient for this week
```

Key prompt engineering techniques used:

1. **Role priming** — "You are an expert restaurant inventory assistant" sets domain context
2. **Schema enforcement** — exact JSON structure with field names and example values
3. **Constraint rules** — explicit definitions for CRITICAL/HIGH/MEDIUM prevent ambiguous classification
4. **Negative instruction** — "no extra text, just valid JSON" reduces preamble/postamble noise
5. **Context injection** — current stock levels are injected as structured key-value pairs

### 4.5 Response Validation

After the LLM returns a response, `ResponseValidator` performs:

- JSON parse validation (regex extraction of `{...}` block, then `json.loads`)
- Schema completeness check (all required fields present)
- Priority value validation (only CRITICAL/HIGH/MEDIUM accepted)
- Hallucination scoring (cross-reference ingredient names against known menu data)

The validator returns a `corrected_response` and a `score` (0.0–1.0). Scores below a threshold trigger a retry via `self_heal.py`.

---

## 5. RAG Pipeline — Menu-Aware Context

### 5.1 Ingestion

When a restaurant uploads a menu PDF via `/api/menu/upload`:

1. `PyPDF2.PdfReader` extracts text from each page
2. If extraction fails (image-based PDF), a fallback OCR mock is used
3. The extracted text is passed to `ai_extract_dishes()` — a Groq call that returns structured JSON with dish names, prices, and ingredients
4. The structured data is saved to PostgreSQL (`MenuDocument` table)
5. The raw text chunks are embedded using `HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")` and stored in ChromaDB

### 5.2 Retrieval

At query time, the chat endpoint performs similarity search:

```python
results = vector_store.similarity_search(query, k=3)
context = "\n".join([r.page_content for r in results])
```

The top-3 most semantically similar menu chunks are prepended to the LLM prompt as context. This allows the model to answer questions like "what dishes use chicken?" without hallucinating — it retrieves actual menu content.

### 5.3 Embedding Model Choice

`all-MiniLM-L6-v2` was chosen because:
- 384-dimensional embeddings — compact and fast
- Strong performance on semantic similarity benchmarks
- Runs locally via HuggingFace, no additional API cost
- Well-suited for short food/ingredient text fragments

---

## 6. Database Layer

### 6.1 Schema Design

Five SQLAlchemy ORM models:

```
User          — restaurant accounts (username, email, restaurant_name)
Product       — inventory items (name, category, unit, current_stock, reorder_level, supplier)
Order         — purchase orders (user_id FK, order_date, total_amount)
OrderDetail   — line items (order_id FK, product_id FK, quantity)
MenuDocument  — uploaded menus (user_id FK, filename, content TEXT, processed_data JSON)
AIInsight     — observability log (query, classification, response_json, created_at)
```

### 6.2 AIInsight — Observability Table

Every AI query is logged to `AIInsight`:

```python
insight = AIInsight(
    query=query,
    classification=classification,
    response_json={'text': response, 'type': 'prediction_table', 'data': predictions}
)
db.session.add(insight)
db.session.commit()
```

This enables:
- Audit trail of all AI decisions
- Replay and debugging of failed queries
- Analytics on classification distribution
- Cost tracking (tokens × price per token)

### 6.3 Technology Choice: PostgreSQL over MongoDB

The system was migrated from MongoDB to PostgreSQL for:
- **Relational integrity** — `OrderDetail` references both `Order` and `Product` with FK constraints
- **JSON column support** — `processed_data JSON` and `response_json JSON` store unstructured AI output alongside structured relational data
- **SQLAlchemy ORM** — single interface for both schema migrations and queries
- **pgAdmin visibility** — easier inspection and debugging during development

---

## 7. Web Application Layer

### 7.1 Flask Routes

15 web pages served via Jinja2 templates:

| Route | Template | Purpose |
|---|---|---|
| `/` | `index.html` | Landing / dashboard entry |
| `/dashboard` | `dashboard.html` | KPI overview |
| `/inventory` | `inventory.html` | Stock levels, reorder alerts |
| `/menu-upload` | `menu_upload.html` | PDF menu ingestion |
| `/chat` | `chat.html` | AI assistant interface |
| `/analytics` | `analytics.html` | Demand forecasting charts |
| `/orders` | `orders.html` | Order history |
| `/recipes` | `recipes.html` | Recipe optimization |
| `/waste-management` | `waste_management.html` | Waste tracking |
| `/reports` | `reports.html` | Inventory value reports |
| `/suppliers` | `suppliers.html` | Supplier management |
| `/staff` | `staff.html` | Staff performance |
| `/settings` | `settings.html` | App configuration |
| `/help` | `help.html` | Documentation |

### 7.2 Key API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/menu/upload` | POST | PDF ingestion → AI extraction → DB save → vector embed |
| `/api/chat/query` | POST | Full AI pipeline: classify → RAG → LLM → validate |
| `/api/inventory/stock` | GET | All products with stock levels |
| `/api/inventory/low-stock` | GET | Products below reorder threshold |
| `/api/analytics/demand-forecast` | GET | 30-day demand projection per product |
| `/api/recipes/optimize` | POST | Substitute low-stock ingredients |
| `/api/observability/logs` | GET | Recent AIInsight records |
| `/api/health` | GET | System health check (LLM + DB + vector store) |

---

## 8. Terminal CLI (run.py)

The terminal runner provides a standalone interface without the web server:

```
─────────────────────────────────────────────
  Kombee  ·  Inventory Assistant
─────────────────────────────────────────────
  Dish name        : paneer korma
  Restaurant name  : Spice Garden
  Current stock  →  ingredient, quantity
  › paneer, 200g
  › tomatoes, 50g
  › [enter]

  Processing…

══════════════════════════════════════════════
  PANEER KORMA — INGREDIENT ORDER LIST
══════════════════════════════════════════════
  Date        2026-03-14
  Restaurant  Spice Garden

  🚨  CRITICAL — ORDER IMMEDIATELY
  ─────────────────────────────────
  1. Tomatoes
     Required       350g
     Current Stock  50g
     Order Qty      300g
     ...
```

The CLI uses `asyncio` for non-blocking LLM calls and exports both PDF (via `fpdf2`) and Word (via `python-docx`) files with the same priority-colour-coded layout.

**PDF colour scheme:**
- CRITICAL sections: `#DC2626` (red)
- HIGH sections: `#D97706` (amber)
- MEDIUM sections: `#6366F1` (indigo)
- Recipe section: `#16A34A` (green)

---

## 9. Configuration and Environment Management

`config/settings.py` uses Pydantic `BaseSettings` for type-safe environment variable loading:

```python
class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "postgresql://...")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    huggingface_api_key: str = os.getenv("HUGGINGFACE_API_KEY", "")
    vector_db_path: str = "./vector_store"
    model_config = ConfigDict(env_file=".env", extra="ignore")
```

Benefits:
- `.env` file support with automatic loading
- Type coercion (string → int for ports, etc.)
- `extra="ignore"` prevents crashes on unknown env vars
- Single source of truth for all configuration

---

## 10. Novel Research Contributions

### 10.1 Multi-Stage LLM Orchestration for Domain-Specific Tasks

Most LLM applications use a single prompt → single response pattern. Nova-Dine implements a **four-stage pipeline** (classify → build context → route → validate) where each stage is independently testable and replaceable. This modular design allows:
- Swapping the classifier without changing the router
- Adding new validators without touching the prompt builder
- A/B testing different models at the routing stage

### 10.2 Priority-Aware Structured Output

The CRITICAL/HIGH/MEDIUM priority taxonomy is enforced at the prompt level with explicit business rules (stock duration thresholds). This transforms a free-text LLM response into an actionable, machine-readable decision tree that can drive automated purchase orders.

### 10.3 Hybrid Storage Architecture

Combining PostgreSQL (relational + JSON columns) with ChromaDB (vector similarity) in a single application allows:
- Exact lookups by product ID or user ID (SQL)
- Semantic search over menu content (vector)
- Structured AI output storage alongside relational data (JSON columns)

### 10.4 Dual-Interface Design

The same AI backbone serves both a web UI (Flask + Jinja2) and a terminal CLI (asyncio + fpdf2 + python-docx). This demonstrates that the orchestration layer is interface-agnostic — a pattern applicable to any AI-native application.

---

## 11. Limitations and Future Work

**Current limitations:**
- Demand forecasting uses random simulation rather than real historical order data
- The RAG pipeline falls back to a hardcoded menu if PDF OCR fails
- No authentication layer — all users share the same `user_id=1` default
- The backbone sub-modules (`engines/`, `validators/`, `models/`) are scaffolded but not fully implemented — the production logic lives in `main_app.py`

**Future work:**
- Implement real time-series demand forecasting (Prophet or LSTM) using `Order` history
- Add OCR support (Tesseract or AWS Textract) for image-based menu PDFs
- Complete the backbone modular implementation for full separation of concerns
- Add JWT authentication and multi-tenant support
- Integrate supplier APIs for real-time pricing and availability
- Add a feedback loop: if a chef overrides an AI recommendation, retrain the priority thresholds
- Extend the RAG pipeline to include nutritional databases for allergen-aware ordering

---

## 12. Tech Stack Summary

| Layer | Technology | Version / Notes |
|---|---|---|
| Web Framework | Flask | Python 3.x, synchronous |
| ORM | SQLAlchemy + Flask-SQLAlchemy | PostgreSQL backend |
| LLM Inference | Groq API | llama-3.3-70b-versatile, llama-3.1-8b-instant |
| LLM Orchestration | LangChain | ChatGroq, HuggingFaceEndpoint |
| Embeddings | HuggingFace | all-MiniLM-L6-v2 (384-dim) |
| Vector Store | ChromaDB | Local persistence |
| PDF Parsing | PyPDF2 | With OCR fallback |
| PDF Generation | fpdf2 | Custom Minimal Tech theme |
| Word Generation | python-docx | Styled tables + numbered recipe |
| Config Management | Pydantic BaseSettings | .env file support |
| Async Runtime | asyncio | Terminal CLI only |
| Frontend | Jinja2 + Bootstrap + Vanilla JS | 15 templates |

---

## 13. Conclusion

Nova-Dine demonstrates that a multi-stage LLM orchestration pipeline, when combined with domain-specific prompt engineering and a hybrid storage architecture, can transform unstructured restaurant queries into structured, actionable inventory decisions. The system's modular backbone design — classifier, router, validator — provides a reusable pattern for any domain where AI output must be reliable, structured, and auditable. The priority-based output format (CRITICAL/HIGH/MEDIUM) bridges the gap between AI inference and real-world operational workflows, making the system immediately usable by restaurant staff without AI expertise.

---

*Nova-Dine — Built for Kombee Hackathon*
*GitHub: https://github.com/pragyankumar-kombee/Nova-Dine*
