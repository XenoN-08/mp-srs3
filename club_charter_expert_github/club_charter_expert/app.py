import streamlit as st
import json
import time
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))

from agents.agent1_extractor import extract_charter_structure
from agents.agent2_compliance import check_compliance
from agents.agent3_improver import generate_improved_charter
from tools.file_parser import parse_uploaded_file
from tools.policy_checker import load_university_policy
from utils.memory import Memory

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Эксперт по уставу студенческого клуба",
    page_icon="📋",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
    }
    .agent-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1.2rem;
        margin: 0.8rem 0;
        background: #f8f9fa;
    }
    .agent-active {
        border-left: 4px solid #2d6a9f;
        background: #eef4fb;
    }
    .agent-done {
        border-left: 4px solid #28a745;
        background: #f0fff4;
    }
    .agent-warn {
        border-left: 4px solid #ffc107;
        background: #fffbf0;
    }
    .section-tag {
        display: inline-block;
        background: #2d6a9f;
        color: white;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        margin: 2px;
    }
    .missing-tag {
        display: inline-block;
        background: #dc3545;
        color: white;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        margin: 2px;
    }
    .risk-item {
        background: #fff3cd;
        border-left: 3px solid #ffc107;
        padding: 8px 12px;
        border-radius: 4px;
        margin: 4px 0;
    }
    .hitl-box {
        background: linear-gradient(135deg, #fff8e1, #fff3cd);
        border: 2px solid #ffc107;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .memory-item {
        background: #e8f4f8;
        padding: 6px 10px;
        border-radius: 6px;
        margin: 4px 0;
        font-size: 0.85rem;
    }
    .stButton > button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ── Initialize session state ──────────────────────────────────────────────────
if "memory" not in st.session_state:
    st.session_state.memory = Memory()
if "stage" not in st.session_state:
    st.session_state.stage = "upload"
if "charter_text" not in st.session_state:
    st.session_state.charter_text = ""
if "policy_text" not in st.session_state:
    st.session_state.policy_text = ""
if "structure" not in st.session_state:
    st.session_state.structure = None
if "compliance" not in st.session_state:
    st.session_state.compliance = None
if "improvements" not in st.session_state:
    st.session_state.improvements = None
if "final_approved" not in st.session_state:
    st.session_state.final_approved = False
if "hitl_comment" not in st.session_state:
    st.session_state.hitl_comment = ""

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>📋 Эксперт по уставу студенческого клуба</h1>
    <p>Многоагентная система анализа и проверки соответствия уставов университетским требованиям</p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar: Memory & Progress ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🧠 Память системы")
    memory_data = st.session_state.memory.get_all()
    if memory_data["typical_issues"]:
        st.markdown("**Типичные замечания:**")
        for issue in memory_data["typical_issues"][-5:]:
            st.markdown(f'<div class="memory-item">⚠️ {issue}</div>', unsafe_allow_html=True)
    if memory_data["approved_clauses"]:
        st.markdown("**Одобренные формулировки:**")
        for clause in memory_data["approved_clauses"][-3:]:
            st.markdown(f'<div class="memory-item">✅ {clause[:60]}...</div>', unsafe_allow_html=True)
    if not memory_data["typical_issues"] and not memory_data["approved_clauses"]:
        st.info("Память пуста. После анализа первого устава система начнёт накапливать знания.")

    st.markdown("---")
    st.markdown("### 📊 Прогресс")
    stages = ["upload", "agent1", "agent2", "conditional", "agent3", "hitl", "done"]
    stage_labels = {
        "upload": "📁 Загрузка файлов",
        "agent1": "🔍 Извлечение структуры",
        "agent2": "✅ Проверка соответствия",
        "conditional": "⚙️ Условная задача",
        "agent3": "📝 Формирование заключения",
        "hitl": "👤 Проверка эксперта (HITL)",
        "done": "🏁 Завершено",
    }
    current_idx = stages.index(st.session_state.stage) if st.session_state.stage in stages else 0
    for i, s in enumerate(stages):
        if i < current_idx:
            st.markdown(f"✅ {stage_labels[s]}")
        elif i == current_idx:
            st.markdown(f"▶️ **{stage_labels[s]}**")
        else:
            st.markdown(f"⬜ {stage_labels[s]}")

# ── STAGE: Upload ─────────────────────────────────────────────────────────────
if st.session_state.stage == "upload":
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📄 Устав клуба")
        charter_file = st.file_uploader(
            "Загрузите проект устава (PDF или DOCX)",
            type=["pdf", "docx"],
            key="charter_upload"
        )
        if charter_file:
            with st.spinner("Извлекаем текст..."):
                text = parse_uploaded_file(charter_file)
            if text:
                st.session_state.charter_text = text
                st.success(f"✅ Файл загружен: {charter_file.name} ({len(text)} символов)")
                with st.expander("Предпросмотр текста"):
                    st.text(text[:1500] + "..." if len(text) > 1500 else text)
            else:
                st.error("Не удалось извлечь текст из файла")

    with col2:
        st.markdown("### 🏛️ Правила университета")
        policy_file = st.file_uploader(
            "Загрузите правила (PDF, DOCX или TXT)",
            type=["pdf", "docx", "txt"],
            key="policy_upload"
        )
        if policy_file:
            with st.spinner("Извлекаем правила..."):
                policy_text = parse_uploaded_file(policy_file)
            if policy_text:
                st.session_state.policy_text = policy_text
                st.success(f"✅ Правила загружены: {policy_file.name}")
                with st.expander("Предпросмотр правил"):
                    st.text(policy_text[:1000] + "..." if len(policy_text) > 1000 else policy_text)
            else:
                st.error("Не удалось прочитать файл правил")
        else:
            if st.button("📋 Использовать правила по умолчанию"):
                st.session_state.policy_text = load_university_policy()
                st.success("✅ Загружены встроенные правила университета")
                with st.expander("Предпросмотр правил"):
                    st.text(st.session_state.policy_text[:1000] + "...")

    st.markdown("---")

    demo_col1, demo_col2 = st.columns(2)
    with demo_col1:
        if st.button("🎭 Демо: устав БЕЗ нарушений (условная задача НЕ сработает)"):
            from utils.demo_data import DEMO_CHARTER_COMPLETE, DEMO_POLICY
            st.session_state.charter_text = DEMO_CHARTER_COMPLETE
            st.session_state.policy_text = DEMO_POLICY
            st.session_state.stage = "agent1"
            st.rerun()
    with demo_col2:
        if st.button("⚠️ Демо: устав С нарушениями (условная задача СРАБОТАЕТ)"):
            from utils.demo_data import DEMO_CHARTER_INCOMPLETE, DEMO_POLICY
            st.session_state.charter_text = DEMO_CHARTER_INCOMPLETE
            st.session_state.policy_text = DEMO_POLICY
            st.session_state.stage = "agent1"
            st.rerun()

    if st.session_state.charter_text and st.session_state.policy_text:
        if st.button("🚀 Запустить анализ", type="primary"):
            st.session_state.stage = "agent1"
            st.rerun()

# ── STAGE: Agent 1 — Structure Extraction ────────────────────────────────────
elif st.session_state.stage == "agent1":
    st.markdown("## 🔍 Агент 1: Извлечение структуры устава")
    st.markdown('<div class="agent-card agent-active">', unsafe_allow_html=True)
    st.markdown("**Цель:** Анализирует загруженный документ и извлекает все разделы устава")
    st.markdown("</div>", unsafe_allow_html=True)

    with st.spinner("Агент 1 анализирует структуру документа..."):
        memory_context = st.session_state.memory.get_all()
        structure = extract_charter_structure(
            st.session_state.charter_text,
            memory_context
        )
        st.session_state.structure = structure
        time.sleep(0.5)

    if structure:
        st.success("✅ Структура успешно извлечена")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Найденные разделы:")
            for section in structure.get("found_sections", []):
                st.markdown(f'<span class="section-tag">✓ {section}</span>', unsafe_allow_html=True)

        with col2:
            st.markdown("### Метаданные:")
            meta = structure.get("metadata", {})
            st.metric("Название клуба", meta.get("club_name", "Не указано"))
            st.metric("Тип клуба", meta.get("club_type", "Не указан"))
            st.metric("Дата документа", meta.get("date", "Не указана"))
            st.metric("Всего разделов", len(structure.get("found_sections", [])))

        if structure.get("raw_summary"):
            with st.expander("Краткое содержание документа"):
                st.write(structure["raw_summary"])

    if st.button("Перейти к проверке соответствия →", type="primary"):
        st.session_state.stage = "agent2"
        st.rerun()

# ── STAGE: Agent 2 — Compliance Check ────────────────────────────────────────
elif st.session_state.stage == "agent2":
    st.markdown("## ✅ Агент 2: Проверка соответствия правилам")
    st.markdown('<div class="agent-card agent-active">', unsafe_allow_html=True)
    st.markdown("**Цель:** Сверяет структуру устава с правилами университета, выявляет нарушения и риски")
    st.markdown("</div>", unsafe_allow_html=True)

    with st.spinner("Агент 2 проверяет соответствие университетским требованиям..."):
        compliance = check_compliance(
            st.session_state.structure,
            st.session_state.policy_text,
            st.session_state.memory.get_all()
        )
        st.session_state.compliance = compliance
        time.sleep(0.5)

    if compliance:
        score = compliance.get("compliance_score", 0)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Оценка соответствия", f"{score}/100",
                     delta=f"{'✅ Проходит' if score >= 70 else '❌ Не проходит'}")
        with col2:
            st.metric("Отсутствующих разделов",
                     len(compliance.get("missing_sections", [])))
        with col3:
            st.metric("Выявленных рисков",
                     len(compliance.get("risks", [])))

        if compliance.get("missing_sections"):
            st.markdown("### ❌ Отсутствующие обязательные разделы:")
            for s in compliance["missing_sections"]:
                st.markdown(f'<span class="missing-tag">✗ {s}</span>', unsafe_allow_html=True)

        if compliance.get("risks"):
            st.markdown("### ⚠️ Выявленные риски:")
            for risk in compliance["risks"]:
                st.markdown(f'<div class="risk-item">⚠️ {risk}</div>', unsafe_allow_html=True)

        if compliance.get("compliant_sections"):
            with st.expander("✅ Разделы в порядке"):
                for s in compliance["compliant_sections"]:
                    st.markdown(f"- ✅ {s}")

        # ── Conditional Task Logic ──────────────────────────────────────────
        needs_corrections = (
            len(compliance.get("missing_sections", [])) > 0 or
            len(compliance.get("risks", [])) > 0 or
            score < 70
        )

        if needs_corrections:
            st.markdown("---")
            st.warning("""
            ⚙️ **Условная задача активирована**

            Обнаружены отсутствующие разделы или риски → автоматически запускается
            агент формирования списка обязательных доработок перед финальным заключением.
            """)
            if st.button("▶ Запустить условную задачу + Агент 3", type="primary"):
                st.session_state.stage = "conditional"
                st.rerun()
        else:
            st.markdown("---")
            st.success("""
            ✅ **Условная задача НЕ требуется**

            Устав полностью соответствует требованиям. Переходим к финальному заключению.
            """)
            if st.button("▶ Перейти к финальному заключению", type="primary"):
                st.session_state.stage = "agent3"
                st.rerun()

# ── STAGE: Conditional Task ───────────────────────────────────────────────────
elif st.session_state.stage == "conditional":
    st.markdown("## ⚙️ Условная задача: Формирование списка доработок")

    st.markdown("""
    <div class="agent-card agent-warn">
    <b>Условная задача сработала, потому что:</b><br>
    Агент 2 выявил отсутствующие обязательные разделы или риски нарушения правил.
    Перед формированием финального заключения система автоматически генерирует
    структурированный список конкретных исправлений, необходимых для регистрации клуба.
    </div>
    """, unsafe_allow_html=True)

    compliance = st.session_state.compliance

    st.markdown("### 📋 Обязательные доработки:")

    if compliance.get("missing_sections"):
        st.markdown("**Раздел 1: Добавить обязательные разделы**")
        for i, s in enumerate(compliance["missing_sections"], 1):
            # Look up approved formulation from memory
            approved = st.session_state.memory.get_approved_clause(s)
            st.markdown(f"**{i}.** Добавить раздел: **«{s}»**")
            if approved:
                st.info(f"💡 Из памяти системы — одобренная формулировка: *{approved}*")

    if compliance.get("risks"):
        st.markdown("**Раздел 2: Устранить выявленные риски**")
        for i, risk in enumerate(compliance["risks"], 1):
            st.markdown(f"**{i}.** {risk}")

    # Save issues to memory
    for issue in compliance.get("missing_sections", []):
        st.session_state.memory.add_typical_issue(f"Отсутствует раздел: {issue}")
    for risk in compliance.get("risks", []):
        st.session_state.memory.add_typical_issue(risk)

    st.success("✅ Список доработок сформирован и сохранён в память системы")

    if st.button("▶ Перейти к формированию заключения", type="primary"):
        st.session_state.stage = "agent3"
        st.rerun()

# ── STAGE: Agent 3 — Improved Charter / Expert Opinion ───────────────────────
elif st.session_state.stage == "agent3":
    st.markdown("## 📝 Агент 3: Формирование экспертного заключения")
    st.markdown('<div class="agent-card agent-active">', unsafe_allow_html=True)
    st.markdown("**Цель:** Готовит улучшенную редакцию устава и экспертное заключение для подачи на регистрацию")
    st.markdown("</div>", unsafe_allow_html=True)

    with st.spinner("Агент 3 формирует заключение и улучшенную редакцию..."):
        improvements = generate_improved_charter(
            st.session_state.charter_text,
            st.session_state.structure,
            st.session_state.compliance,
            st.session_state.memory.get_all()
        )
        st.session_state.improvements = improvements
        time.sleep(0.5)

    if improvements:
        st.success("✅ Экспертное заключение подготовлено")

        tab1, tab2, tab3 = st.tabs(["📋 Заключение", "✏️ Улучшенная редакция", "📊 Сводка"])

        with tab1:
            st.markdown("### Экспертное заключение")
            st.write(improvements.get("expert_opinion", ""))

        with tab2:
            st.markdown("### Предлагаемые изменения")
            changes = improvements.get("proposed_changes", [])
            for change in changes:
                with st.expander(f"📌 {change.get('section', '')}"):
                    st.markdown(f"**Проблема:** {change.get('issue', '')}")
                    st.markdown(f"**Предложение:** {change.get('suggestion', '')}")
                    if change.get("example"):
                        st.code(change["example"], language=None)

        with tab3:
            col1, col2 = st.columns(2)
            with col1:
                score = st.session_state.compliance.get("compliance_score", 0)
                st.metric("Текущая оценка", f"{score}/100")
                st.metric("Оценка после исправлений",
                         f"{improvements.get('projected_score', score + 20)}/100")
            with col2:
                st.metric("Рекомендация",
                         improvements.get("recommendation", "На доработку"))

    if st.button("▶ Передать на финальное одобрение (HITL)", type="primary"):
        st.session_state.stage = "hitl"
        st.rerun()

# ── STAGE: HITL ───────────────────────────────────────────────────────────────
elif st.session_state.stage == "hitl":
    st.markdown("## 👤 HITL: Финальное одобрение эксперта")

    st.markdown("""
    <div class="hitl-box">
    <h4>🔴 Требуется участие человека-эксперта</h4>
    <p>Данный этап требует <b>проверки живым специалистом</b>, поскольку выводы системы
    могут повлиять на решение об официальной регистрации студенческого клуба.
    Автоматическое решение недопустимо — ошибка влечёт юридические и организационные последствия.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### Сводка для эксперта")
        comp = st.session_state.compliance or {}
        impr = st.session_state.improvements or {}

        score = comp.get("compliance_score", 0)
        rec = impr.get("recommendation", "Требует проверки")

        st.markdown(f"**Оценка соответствия:** {score}/100")
        st.markdown(f"**Рекомендация системы:** {rec}")
        st.markdown(f"**Отсутствующих разделов:** {len(comp.get('missing_sections', []))}")
        st.markdown(f"**Выявленных рисков:** {len(comp.get('risks', []))}")

        if impr.get("expert_opinion"):
            st.markdown("**Заключение агента 3:**")
            st.info(impr["expert_opinion"][:600] + "...")

        hitl_comment = st.text_area(
            "Комментарий эксперта (обязательно):",
            placeholder="Введите ваши замечания, решение и основание...",
            height=120,
            key="hitl_text"
        )
        st.session_state.hitl_comment = hitl_comment

    with col2:
        st.markdown("### Решение эксперта")
        st.markdown("---")

        if st.button("✅ ОДОБРИТЬ\n(рекомендовать к регистрации)", type="primary"):
            if st.session_state.hitl_comment.strip():
                # Save approved formulations to memory
                if st.session_state.improvements:
                    for change in st.session_state.improvements.get("proposed_changes", []):
                        if change.get("example"):
                            st.session_state.memory.add_approved_clause(
                                f"{change['section']}: {change['example'][:80]}"
                            )
                st.session_state.final_approved = True
                st.session_state.stage = "done"
                st.rerun()
            else:
                st.error("Введите комментарий эксперта перед принятием решения")

        st.markdown("")

        if st.button("❌ ОТКЛОНИТЬ\n(требует доработки)"):
            if st.session_state.hitl_comment.strip():
                st.session_state.memory.add_typical_issue(
                    f"Отклонено экспертом: {st.session_state.hitl_comment[:100]}"
                )
                st.session_state.final_approved = False
                st.session_state.stage = "done"
                st.rerun()
            else:
                st.error("Введите комментарий эксперта перед принятием решения")

        st.markdown("")

        if st.button("🔄 Вернуть на доработку"):
            st.session_state.stage = "agent3"
            st.rerun()

# ── STAGE: Done ───────────────────────────────────────────────────────────────
elif st.session_state.stage == "done":
    approved = st.session_state.final_approved

    if approved:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#28a745,#20c997);padding:2rem;border-radius:12px;color:white;text-align:center;">
        <h2>✅ УСТАВ ОДОБРЕН</h2>
        <p>Документ рекомендован к регистрации. Заключение эксперта сохранено.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#dc3545,#c82333);padding:2rem;border-radius:12px;color:white;text-align:center;">
        <h2>❌ УСТАВ ОТКЛОНЁН</h2>
        <p>Документ требует доработки. Список замечаний сохранён в памяти системы.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### Комментарий эксперта:")
    st.info(st.session_state.hitl_comment)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Начать новый анализ"):
            for key in ["stage", "charter_text", "policy_text", "structure",
                        "compliance", "improvements", "final_approved", "hitl_comment"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.stage = "upload"
            st.rerun()
    with col2:
        comp = st.session_state.compliance or {}
        impr = st.session_state.improvements or {}
        report_data = {
            "decision": "ОДОБРЕН" if approved else "ОТКЛОНЁН",
            "expert_comment": st.session_state.hitl_comment,
            "compliance_score": comp.get("compliance_score", 0),
            "missing_sections": comp.get("missing_sections", []),
            "risks": comp.get("risks", []),
            "recommendation": impr.get("recommendation", ""),
            "expert_opinion": impr.get("expert_opinion", ""),
        }
        st.download_button(
            "📥 Скачать JSON-отчёт",
            data=json.dumps(report_data, ensure_ascii=False, indent=2),
            file_name="charter_review_report.json",
            mime="application/json"
        )

    st.markdown("### 🧠 Память обновлена:")
    mem = st.session_state.memory.get_all()
    st.json(mem)
