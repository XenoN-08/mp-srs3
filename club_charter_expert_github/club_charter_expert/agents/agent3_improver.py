"""
Agent 3: Charter Improver & Expert Opinion Generator
Produces specific improvement suggestions and a formal expert opinion.
"""
import json, re, requests

SYSTEM_PROMPT = """Ты — опытный юрист и эксперт по уставам студенческих организаций.
На основе анализа устава и выявленных нарушений подготовь заключение.
Верни ТОЛЬКО JSON (без markdown-обёртки):

{
  "expert_opinion": "формальное экспертное заключение (3-5 предложений)",
  "proposed_changes": [
    {
      "section": "название раздела",
      "issue": "выявленная проблема",
      "suggestion": "конкретное предложение по исправлению",
      "example": "пример формулировки (если уместно)"
    }
  ],
  "projected_score": число от 0 до 100 (ожидаемый балл после исправлений),
  "recommendation": "ОДОБРИТЬ / ОДОБРИТЬ С УСЛОВИЯМИ / НА ДОРАБОТКУ / ОТКЛОНИТЬ"
}
"""


def generate_improved_charter(
    charter_text: str,
    structure: dict,
    compliance: dict,
    memory_context: dict
) -> dict:
    if not compliance:
        return _fallback_improvements(compliance)

    missing = compliance.get("missing_sections", [])
    risks = compliance.get("risks", [])
    score = compliance.get("compliance_score", 50)

    approved_hint = ""
    if memory_context.get("approved_clauses"):
        approved_hint = f"\nПримеры одобренных формулировок из прошлых уставов: {'; '.join(memory_context['approved_clauses'][:2])}"

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1000,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": (
                    f"Оценка соответствия: {score}/100\n"
                    f"Отсутствующие разделы: {missing}\n"
                    f"Выявленные риски: {risks}\n"
                    f"{approved_hint}\n\n"
                    f"Фрагмент устава:\n{charter_text[:2000]}\n\n"
                    "Подготовь экспертное заключение и предложения по улучшению."
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
        return _fallback_improvements(compliance)


def _fallback_improvements(compliance: dict) -> dict:
    if not compliance:
        return {
            "expert_opinion": "Не удалось получить данные для анализа.",
            "proposed_changes": [],
            "projected_score": 0,
            "recommendation": "НА ДОРАБОТКУ"
        }

    missing = compliance.get("missing_sections", [])
    risks = compliance.get("risks", [])
    score = compliance.get("compliance_score", 50)

    changes = []
    for section in missing:
        changes.append({
            "section": section,
            "issue": f"Раздел «{section}» отсутствует в документе",
            "suggestion": f"Добавить раздел «{section}» с чёткими процедурами",
            "example": f"Раздел {len(changes)+1}. {section}: [описание порядка и процедур]"
        })
    for risk in risks:
        changes.append({
            "section": "Общие замечания",
            "issue": risk,
            "suggestion": "Устранить выявленный риск путём уточнения соответствующих положений",
            "example": ""
        })

    if score >= 90:
        rec = "ОДОБРИТЬ"
    elif score >= 70:
        rec = "ОДОБРИТЬ С УСЛОВИЯМИ"
    elif score >= 50:
        rec = "НА ДОРАБОТКУ"
    else:
        rec = "ОТКЛОНИТЬ"

    projected = min(100, score + len(changes) * 8)
    opinion = (
        f"Представленный устав набрал {score}/100 баллов по критериям соответствия. "
        f"Выявлено {len(missing)} отсутствующих разделов и {len(risks)} рисков. "
        f"Рекомендация: {rec}."
    )

    return {
        "expert_opinion": opinion,
        "proposed_changes": changes,
        "projected_score": projected,
        "recommendation": rec
    }
