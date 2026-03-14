"""
backbone/router/model_router.py
Routes queries to the appropriate Groq model based on classification + complexity.
"""
import os
import time
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv()

# Active Groq models
HEAVY_MODEL  = "llama-3.3-70b-versatile"   # complex reasoning, structured JSON
LIGHT_MODEL  = "llama-3.1-8b-instant"      # fast classification, simple lookups

# Use heavy model for these use cases
HEAVY_USE_CASES = {"MENU", "ORDER", "GENERAL"}


class AdvancedRouter:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY is not set in environment / .env")

        self._heavy = ChatGroq(temperature=0.1, model_name=HEAVY_MODEL, groq_api_key=api_key)
        self._light = ChatGroq(temperature=0,   model_name=LIGHT_MODEL,  groq_api_key=api_key)

    async def route(self, classification, prompt: str, context: dict = None) -> dict:
        use_heavy = (
            classification.use_case in HEAVY_USE_CASES
            or classification.complexity == "COMPLEX"
        )
        model = self._heavy if use_heavy else self._light
        model_name = HEAVY_MODEL if use_heavy else LIGHT_MODEL

        system_msg = SystemMessage(content=(
            "You are an expert restaurant inventory assistant. "
            "Always respond with valid JSON only — no markdown, no extra text."
        ))

        start = time.time()
        try:
            response = model.invoke([system_msg, HumanMessage(content=prompt)])
            elapsed = round(time.time() - start, 2)
            content = response.content
            tokens  = getattr(response, "usage_metadata", {})
            total_tokens = (tokens.get("input_tokens", 0) + tokens.get("output_tokens", 0)
                            if isinstance(tokens, dict) else 0)
            return {
                "response":   content,
                "model_used": model_name,
                "cached":     False,
                "cost":       round(total_tokens * 0.000001, 6),
                "time_taken": elapsed,
                "tokens_used": total_tokens,
            }
        except Exception as e:
            return {
                "response":   f'{{"error": "{str(e)}"}}',
                "model_used": model_name,
                "cached":     False,
                "cost":       0,
                "time_taken": round(time.time() - start, 2),
                "tokens_used": 0,
            }
