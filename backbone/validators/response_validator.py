"""
backbone/validators/response_validator.py
Validates and corrects LLM responses — JSON parse, schema check, priority values.
"""
import json
import re


REQUIRED_FIELDS = {"name", "required", "current_stock", "order_quantity",
                   "supplier", "cost_inr", "priority"}
VALID_PRIORITIES = {"CRITICAL", "HIGH", "MEDIUM"}


class ResponseValidator:
    async def validate(self, response: str, use_case: str = "GENERAL") -> dict:
        parsed, score, warnings = self._parse_json(response)

        if parsed and "ingredients" in parsed:
            score, warnings = self._validate_schema(parsed, score, warnings)
            parsed = self._fix_priorities(parsed)

        return {
            "corrected_response": json.dumps(parsed) if parsed else response,
            "score": score,
            "warnings": warnings,
            "valid_json": parsed is not None,
        }

    # ── helpers ──────────────────────────────────────────────────────────────

    def _parse_json(self, text: str):
        # Strip markdown fences if present
        text = re.sub(r"```json|```", "", text).strip()
        # Find outermost { ... }
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return None, 0.0, ["No JSON block found in response"]
        try:
            return json.loads(m.group()), 1.0, []
        except json.JSONDecodeError as e:
            return None, 0.0, [f"JSON parse error: {e}"]

    def _validate_schema(self, data: dict, score: float, warnings: list):
        ingredients = data.get("ingredients", [])
        if not ingredients:
            warnings.append("No ingredients in response")
            score -= 0.3
            return score, warnings

        for i, ing in enumerate(ingredients):
            missing = REQUIRED_FIELDS - set(ing.keys())
            if missing:
                warnings.append(f"Ingredient {i} missing fields: {missing}")
                score -= 0.05

        if "total_cost_inr" not in data:
            warnings.append("Missing total_cost_inr")
            score -= 0.05

        return max(score, 0.0), warnings

    def _fix_priorities(self, data: dict) -> dict:
        """Normalise priority values to uppercase and fix typos."""
        for ing in data.get("ingredients", []):
            p = str(ing.get("priority", "MEDIUM")).upper().strip()
            if p not in VALID_PRIORITIES:
                # Best-effort mapping
                if "CRIT" in p:
                    p = "CRITICAL"
                elif "HIGH" in p:
                    p = "HIGH"
                else:
                    p = "MEDIUM"
            ing["priority"] = p
        return data
