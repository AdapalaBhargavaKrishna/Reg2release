import json
import os
import copy

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "mock_rules.json")

class RuleStore:
    """Mock carrier rule repository storing versioned insurance rules as JSON."""

    def __init__(self, data_path=None):
        self.data_path = data_path or DATA_PATH
        self.rules = self._load_rules()

    def _load_rules(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def get_all_rules(self):
        return self.rules

    def get_rule_by_id(self, rule_id: str):
        for r in self.rules:
            if r["rule_id"].lower() == rule_id.lower():
                return copy.deepcopy(r)
        return None

    def search_rules(self, query: str = "", jurisdiction: str = "", line_of_business: str = ""):
        """Finds candidate rules matching query tokens, line of business, or jurisdiction."""
        matches = []
        tokens = query.lower().split()

        for r in self.rules:
            score = 0
            # Line of business match
            if line_of_business and line_of_business.lower() in r["line_of_business"].lower():
                score += 3
            # Jurisdiction match
            if jurisdiction and (jurisdiction.lower() in r["jurisdiction"].lower() or r["jurisdiction"] == "US - Nationwide"):
                score += 3
            # Token match across id, name, description
            searchable_text = f"{r['rule_id']} {r['rule_name']} {r['description']} {json.dumps(r['parameters'])}".lower()
            for token in tokens:
                if len(token) > 2 and token in searchable_text:
                    score += 1

            matches.append((score, r))

        # Sort by relevance score descending
        matches.sort(key=lambda x: x[0], reverse=True)
        return [m[1] for m in matches if m[0] > 0] or self.rules

    def create_proposed_rule(self, base_rule_id: str, new_parameters: dict, new_version: str = None):
        base = self.get_rule_by_id(base_rule_id)
        if not base:
            raise ValueError(f"Rule ID {base_rule_id} not found.")

        current_ver = float(base.get("version", "1.0"))
        proposed_ver = new_version or f"{current_ver + 0.1:.1f}"

        proposed_rule = copy.deepcopy(base)
        proposed_rule["version"] = proposed_ver
        proposed_rule["status"] = "PROPOSED"
        proposed_rule["parameters"].update(new_parameters)
        return proposed_rule
