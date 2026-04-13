"""
Agent 2: Compliance Checker
Verifies the charter structure against university policy rules.
"""
import json, re, requests

REQUIRED_SECTIONS = [
    "Наименование",
    "Цели и задачи",
    "Членство",
    "Руководство",
    "Финансирование",
    "Прекращение деятельности",
    "Изменение устава",
    "Этика и поведение",
    "Безопасность",
    "Отчётность",
]

SYSTEM_PROMPT = """Ты — агент проверки соответствия уставов студенческих клубов.
Проверь устав по правилам университета. Верни ТОЛЬКО JSON (без markdown-обёртки):

{
  "compliance_score": число от 0 до 100,
  "missing_sections": ["отсутствующие обязательные разделы"],
  "risks": ["конкретные риски нарушения правил"],
  "compliant_sections": ["разделы, соответствующие требованиям"],
  "summary": "краткий вывод о соответствии"
}

Обязательные разделы: Наименование, Цели и задачи, Членство, Руководство,
Финансирование, Прекращение деятельности, Изменение устава, Этика и поведение,
Безопасность, Отчётность.

Типичные риски: дискриминация, нет механизма апелляции, неясные финансовые процедуры,
отсутствие требований безопасности, конфликт интересов в руководстве.
"""


def check_compliance(structure: dict, policy_text: str, memory_context: dict) -> dict:
    if not structure:
        return _fallback_compliance([], policy_text)

    found_sections = structure.get("found_sections", [])

    memory_hint = ""
    if memory_context.get("typical_issues"):
        memory_hint = f"\nИз прошлых проверок: типичные проблемы — {'; '.join(memory_context['typical_issues'][-3:])}"

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1000,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": (
                    f"Найденные разделы устава: {found_sections}\n\n"
                    f"Правила университета:\n{policy_text[:2000]}\n\n"
                    f"{memory_hint}\n\n"
                    "Проверь соответствие и верни JSON."
                )
            }
        ]
    }

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        raw = data["content"][0]["text"].strip()
        raw = re.sub(r"```json\s*|\s*```", "", raw).strip()
        return json.loads(raw)
    except Exception:
        return _fallback_compliance(found_sections, policy_text)


def _fallback_compliance(found_sections: list, policy_text: str) -> dict:
    missing = [s for s in REQUIRED_SECTIONS if s not in found_sections]
    present = [s for s in REQUIRED_SECTIONS if s in found_sections]
    score = int((len(present) / len(REQUIRED_SECTIONS)) * 100)

    risks = []
    policy_lower = policy_text.lower()
    if "дискриминация" in policy_lower and "этика" not in " ".join(found_sections).lower():
        risks.append("Отсутствует антидискриминационная политика")
    if "финанс" not in " ".join(found_sections).lower():
        risks.append("Неясные финансовые процедуры")

    return {
        "compliance_score": score,
        "missing_sections": missing,
        "risks": risks,
        "compliant_sections": present,
        "summary": f"Найдено {len(present)} из {len(REQUIRED_SECTIONS)} обязательных разделов."
    }
