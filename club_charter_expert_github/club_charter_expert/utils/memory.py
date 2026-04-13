"""
Memory: Persistent in-session memory for the multi-agent system.
Stores typical issues and approved clause formulations across charter reviews.
"""
import json
import os


MEMORY_FILE = os.path.join(os.path.dirname(__file__), "..", "memory_store.json")


class Memory:
    def __init__(self):
        self._data = {"typical_issues": [], "approved_clauses": {}}
        self._load()

    def _load(self):
        try:
            if os.path.exists(MEMORY_FILE):
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
        except Exception:
            self._data = {"typical_issues": [], "approved_clauses": {}}

    def _save(self):
        try:
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_typical_issue(self, issue: str):
        if issue and issue not in self._data["typical_issues"]:
            self._data["typical_issues"].append(issue)
            # Keep last 20
            self._data["typical_issues"] = self._data["typical_issues"][-20:]
            self._save()

    def add_approved_clause(self, clause: str, section: str = "general"):
        if clause:
            if section not in self._data["approved_clauses"]:
                self._data["approved_clauses"][section] = []
            clauses = self._data["approved_clauses"][section]
            if clause not in clauses:
                clauses.append(clause)
                clauses = clauses[-10:]
                self._data["approved_clauses"][section] = clauses
            self._save()

    def get_approved_clause(self, section: str) -> str:
        """Return the latest approved clause for a section, if any."""
        clauses = self._data["approved_clauses"].get(section, [])
        return clauses[-1] if clauses else ""

    def get_all(self) -> dict:
        # Flatten approved_clauses for easy consumption
        all_clauses = []
        for section_clauses in self._data["approved_clauses"].values():
            all_clauses.extend(section_clauses)
        return {
            "typical_issues": self._data["typical_issues"],
            "approved_clauses": all_clauses,
        }
