"""
backbone/classifier.py
Classifies incoming queries into intent categories and complexity levels.
"""
import os
from dataclasses import dataclass
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Classification:
    use_case: str       # MENU | INVENTORY | PREDICTION | ORDER | GENERAL
    complexity: str     # SIMPLE | COMPLEX
    confidence: float   # 0.0 – 1.0


class EnhancedClassifier:
    CATEGORIES = ["MENU", "INVENTORY", "PREDICTION", "ORDER", "GENERAL"]

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY", "")
        self._llm = ChatGroq(
            temperature=0,
            model_name="llama-3.1-8b-instant",   # fast model for classification
            groq_api_key=api_key,
        ) if api_key else None

    async def classify(self, query: str) -> Classification:
        use_case = self._classify_use_case(query)
        complexity = self._score_complexity(query)
        return Classification(use_case=use_case, complexity=complexity, confidence=0.9)

    def _classify_use_case(self, query: str) -> str:
        if not self._llm:
            return self._keyword_fallback(query)
        prompt = (
            f"Classify this restaurant query into exactly one category: "
            f"MENU, INVENTORY, PREDICTION, ORDER, or GENERAL.\n"
            f"Query: '{query}'\n"
            f"Return ONLY the category word, nothing else."
        )
        try:
            res = self._llm.invoke([HumanMessage(content=prompt)]).content.strip().upper()
            for cat in self.CATEGORIES:
                if cat in res:
                    return cat
        except Exception:
            pass
        return self._keyword_fallback(query)

    def _score_complexity(self, query: str) -> str:
        """Simple heuristic: long queries or multi-ingredient queries are COMPLEX."""
        words = query.split()
        if len(words) > 15 or any(w in query.lower() for w in ["recipe", "steps", "how to", "all ingredients"]):
            return "COMPLEX"
        return "SIMPLE"

    def _keyword_fallback(self, query: str) -> str:
        q = query.lower()
        if any(w in q for w in ["menu", "dish", "recipe", "cook", "make", "prepare"]):
            return "MENU"
        if any(w in q for w in ["stock", "inventory", "available", "how much"]):
            return "INVENTORY"
        if any(w in q for w in ["predict", "forecast", "next week", "demand"]):
            return "PREDICTION"
        if any(w in q for w in ["order", "buy", "purchase", "restock", "supplier"]):
            return "ORDER"
        return "GENERAL"
