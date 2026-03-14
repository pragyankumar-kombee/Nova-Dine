# System Architecture

The Kombee AI Inventory Assistant follows a modular service-oriented architecture.

## Components
1. **Flask API Layer**: Handles HTTP requests, file uploads, and routing.
2. **Service Layer**: Business logic and AI orchestration.
   - `MenuService`: Text extraction & LLM-based ingredient extraction.
   - `InventoryService`: Stock management and lookups.
   - `PredictionService`: Time-series usage forecasting.
3. **Database Layer**: SQLAlchemy ORM with a Postgres backend.
4. **AI Backbone**: Uses Groq (Llama 3.3) for complex reasoning tasks.
