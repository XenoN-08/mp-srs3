"""
Agent 1: Charter Structure Extractor
Calls the Anthropic API to extract sections and metadata from a charter document.
"""
import os, json, re
import requests


SYSTEM_PROMPT = """Ты — агент извлечения структуры уставов студенческих клубов.
Твоя задача: проанализировать текст устава и вернуть ТОЛЬКО JSON (без markdown-обёртки).

Обязательные поля в ответе:
{
  "found_sections": ["список найденных разделов"],
  "metadata": {
    "club_name": "название клуба или 'Не указано'",
    "club_type": "тип клуба или 'Не указан'",
    "date": "дата документа или 'Не указана'"
  },
  "raw_summary": "краткое резюме документа в 2-3 предложениях"
}

Типичные разделы устава: Наименование, Цели и задачи, Членство, Руководство,
Финансирование, Прекращение деятельности, Изменение устава, Этика и поведение,
Безопасность, Отчётность.
"""


def extract_charter_structure(charter_text: str, memory_context: dict) -> dict:
    memory_hint = ""
    if memory_context.get("typical_issues"):
        memory_hint = f"\n\nИз предыдущих анализов известно, что часто встречаются проблемы: {', '.join(memory_context['typical_issues'][-3:])}"

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1000,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": f"Извлеки структуру следующего устава:{memory_hint}\n\n---\n{charter_text[:4000]}\n---"
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
    except Exception as e:
        # Fallback: simple heuristic extraction
        return _heuristic_extract(charter_text)


def _heuristic_extract(text: str) -> dict:
    """Fallback extraction using keyword matching."""
    section_keywords = {
        "Наименование": ["наименование", "название"],
        "Цели и задачи": ["цель", "задачи", "назначение"],
        "Членство": ["членство", "член клуба", "вступление", "приём"],
        "Руководство": ["руководство", "президент", "председатель", "совет"],
        "Финансирование": ["финансирование", "взносы", "бюджет", "средства"],
        "Прекращение деятельности": ["ликвидация", "прекращение", "роспуск"],
        "Изменение устава": ["изменение устава", "поправки", "редакция"],
        "Этика и поведение": ["этика", "кодекс", "поведение", "дисциплина"],
        "Безопасность": ["безопасность", "охрана", "защита"],
        "Отчётность": ["отчёт", "отчётность", "документация"],
    }
    text_lower = text.lower()
    found = [s for s, kws in section_keywords.items() if any(k in text_lower for k in kws)]

    # Try to extract club name
    name_match = re.search(r'(?:клуб|организация|объединение)["\s«]+([^»"\n]{3,50})', text, re.I)
    club_name = name_match.group(1).strip() if name_match else "Не указано"

    return {
        "found_sections": found,
        "metadata": {"club_name": club_name, "club_type": "Не указан", "date": "Не указана"},
        "raw_summary": f"Документ содержит {len(found)} из 10 стандартных разделов устава."
    }
