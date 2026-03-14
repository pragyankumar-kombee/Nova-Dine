# backbone/orchestrator.py
import asyncio
from backbone.classifier import EnhancedClassifier
from backbone.router import AdvancedRouter
from backbone.validators import ResponseValidator


class AIOrchestrator:
    def __init__(self):
        self.classifier = EnhancedClassifier()
        self.router = AdvancedRouter()
        self.validator = ResponseValidator()

    async def process(self, query: str, context: dict = None) -> dict:
        classification = await self.classifier.classify(query)
        prompt = self._build_prompt(query, context)
        result = await self.router.route(classification, prompt, context)
        validation = await self.validator.validate(result["response"], classification.use_case)

        return {
            "query": query,
            "response": validation["corrected_response"],
            "use_case": classification.use_case,
            "model_used": result.get("model_used", "unknown"),
            "cached": result.get("cached", False),
            "cost": result.get("cost", 0),
            "time_taken": result.get("time_taken", 0),
            "tokens_used": result.get("tokens_used", 0),
            "validation_score": validation["score"],
            "warnings": validation.get("warnings", []),
        }

    def _build_prompt(self, query: str, context: dict = None) -> str:
        if not context:
            return query

        stock = context.get("current_stock", {})
        stock_lines = "\n".join(f"  - {item}: {qty}" for item, qty in stock.items()) if stock else "  (none provided)"
        restaurant = context.get("restaurant_name", "Restaurant")
        dish = context.get("dish", "the dish")

        return f"""You are an expert restaurant inventory assistant. Analyze the current stock and provide a detailed ingredient order list for {dish}.

Restaurant: {restaurant}
Current Stock:
{stock_lines}

Return your response in this EXACT JSON format (no extra text, just valid JSON):
{{
  "ingredients": [
    {{
      "name": "ingredient name",
      "required": "amount needed per batch (e.g. 350g)",
      "current_stock": "amount in stock (e.g. 50g, or 0g if none)",
      "order_quantity": "recommended order amount",
      "supplier": "suggested supplier name",
      "cost_inr": 60,
      "priority": "CRITICAL|HIGH|MEDIUM",
      "note": "short note about urgency or usage"
    }}
  ],
  "recipe_steps": [
    "Step 1: ...",
    "Step 2: ..."
  ],
  "total_cost_inr": 395
}}

Rules:
- CRITICAL = stock will run out within 1 day or is completely out
- HIGH = stock will last 2-3 more servings
- MEDIUM = stock is low but sufficient for this week
- Include ALL ingredients needed for {dish} (spices, oil, garnish, etc.)
- recipe_steps should be clear cooking instructions (6-10 steps)
- Be specific with quantities and realistic Indian supplier names
"""
