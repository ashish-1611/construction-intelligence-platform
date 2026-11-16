"""Multimodal Construction Intelligence Platform - Streamlit interface (Milestone 6)."""
from __future__ import annotations

import dataclasses
from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

from construction_ai.assistant import ConstructionChatbot, generate_daily_briefing
from construction_ai.config import get_settings
from construction_ai.costing import estimate_cost, format_inr
from construction_ai.cracks import classify_cracks, heuristic_crack_score
from construction_ai.gemini_client import GeminiClient, GeminiError
from construction_ai.image_utils import ImageError, load_image
from construction_ai.materials import QUALITIES, estimate_materials
from construction_ai.reasoning import extract_plan_details, reason_about_site
from construction_ai.safety import analyze_safety, sort_violations
from construction_ai.scheduler import (
    ScheduleError, Task, build_schedule, default_residential_tasks, project_finish,
)
from construction_ai.weather import (
    WeatherError, assess_day, fetch_forecast, geocode, rain_stop_dates,
)

st.set_page_config(page_title="Construction Intelligence Platform", page_icon="🏗️", layout="wide")

RISK_ICON = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
LEVEL_ICON = {"ok": "🟢", "caution": "🟡", "stop": "🔴"}


# ------------------------------------------------------------------ helpers
def get_client() -> GeminiClient | None:
    """Return a GeminiClient or None (and a hint) when AI is not configured."""
    settings = get_settings()
    key = st.session_state.get("api_key_input", "").strip()
    if key:
        settings = dataclasses.replace(settings, api_key=key)
    if not settings.ai_enabled:
        return None
    cached = st.session_state.get("_client")
    if cached is None or cached.settings != settings:
        cached = GeminiClient(settings)
        st.session_state["_client"] = cached
    return cached


def need_ai() -> GeminiClient | None:
    client = get_client()
    if client is None:
        st.warning("AI features need a Gemini key. Add `GOOGLE_API_KEY` to `.env` or paste it in the sidebar.")
    return client


def read_images(files) -> list:
    out = []
    for f in files or []:
        try:
            out.append(load_image(f.getvalue(), f.name))
        except ImageError as exc:
            st.error(str(exc))
    return out


def run_ai(fn, *args, **kwargs):
    try:
        with st.spinner("Analysing with Gemini..."):
            return fn(*args, **kwargs)
    except GeminiError as exc:
        st.error(str(exc))
        return None


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.title("🏗️ Construction AI")
    st.caption("Multimodal Construction Intelligence Platform")
    project_name = st.text_input("Project name", "My Construction Project")
    city = st.text_input("Site city", "Bhopal")
    st.text_input("Gemini API key (optional)", type="password", key="api_key_input",
                  help="Only kept in this browser session. You can also set GOOGLE_API_KEY in .env.")
    st.success("AI connected") if get_client() else st.info("AI offline: estimation, scheduling and weather still work.")
    st.divider()
    st.caption("AI output is decision support only. Structural and safety decisions must be confirmed by a qualified engineer.")

st.title("Multimodal Construction Intelligence Platform")

tab_site, tab_crack, tab_est, tab_sched, tab_chat, tab_weather = st.tabs(
    ["📷 Site Analysis", "🧱 Crack Detection", "💰 Estimation (INR)", "📅 Schedule", "🤖 Assistant", "🌦️ Weather"]
)

# ------------------------------------------------------------ site analysis
with tab_site:
    st.subheader("Safety inspection & multimodal reasoning")
    files = st.file_uploader("Upload site photos", type=["png", "jpg", "jpeg", "webp"],
                             accept_multiple_files=True, key="site_files")
    mode = st.radio("Mode", ["Safety inspection", "Ask a question about the site"], horizontal=True)
    note = st.text_area("Notes / question", placeholder="e.g. Is this scaffolding safe? What stage is the building at?")
    if st.button("Analyse", type="primary", key="site_go") and files:
        client = need_ai()
        imgs = read_images(files)
        if client and imgs:
            if mode == "Safety inspection":
                rep = run_ai(analyze_safety, client, imgs, note)
                if rep:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Overall risk", f"{RISK_ICON[rep.overall_risk]} {rep.overall_risk.title()}")
                    c2.metric("Workers detected", rep.workers_detected)
                    c3.metric("Confidence", f"{rep.confidence:.0%}")
                    st.write("**PPE:**", rep.ppe_summary)
                    if rep.violations:
                        st.dataframe(pd.DataFrame([
                            {"Severity": f"{RISK_ICON[v.severity]} {v.severity}", "Category": v.category,
                             "Issue": v.description, "Where": v.location_hint, "Fix": v.corrective_action}
                            for v in sort_violations(rep)]), use_container_width=True, hide_index=True)
                    else:
                        st.success("No violations identified.")
                    if rep.compliant_observations:
                        st.write("**Compliant:**", "; ".join(rep.compliant_observations))
                    st.download_button("Download JSON", rep.model_dump_json(indent=2), "safety_report.json")
            else:
                ins = run_ai(reason_about_site, client, imgs, note)
                if ins:
                    st.write(f"**Stage:** {ins.construction_stage}  |  **Confidence:** {ins.confidence:.0%}")
                    st.write(ins.summary)
                    for title, items in [("Observations", ins.observations), ("Risks", ins.risks),
                                         ("Recommended actions", ins.recommended_actions), ("Assumptions", ins.assumptions)]:
                        st.markdown(f"**{title}**")
                        st.markdown("\n".join(f"- {i}" for i in items) or "- none")
                    st.download_button("Download JSON", ins.model_dump_json(indent=2), "site_insight.json")

# ---------------------------------------------------------- crack detection
with tab_crack:
    st.subheader("Crack detection")
    f = st.file_uploader("Upload a wall / slab / column photo", type=["png", "jpg", "jpeg", "webp"], key="crack_file")
    ctx = st.text_input("Context (optional)", placeholder="e.g. 2nd-floor column, appeared after monsoon")
    if f:
        imgs = read_images([f])
        if imgs:
            st.image(imgs[0].data, width=420)
            h = heuristic_crack_score(imgs[0].data)
            st.metric("Offline screening score", f"{h.score:.2f}  ({h.level})")
            st.caption("Quick edge/dark-line heuristic for triage only. Use the AI classification below for a real assessment.")
            if st.button("Classify with AI", type="primary", key="crack_go"):
                client = need_ai()
                if client:
                    r = run_ai(classify_cracks, client, imgs[0], ctx)
                    if r:
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Crack detected", "Yes" if r.crack_detected else "No")
                        c2.metric("Severity", f"{RISK_ICON[r.severity]} {r.severity.title()}")
                        c3.metric("Type", r.crack_type.replace("_", " ").title())
                        st.write(f"**Estimated width:** {r.estimated_width_mm}  |  **Element:** {r.affected_element}")
                        st.write("**Likely causes:**", "; ".join(r.likely_causes) or "n/a")
                        st.write("**Recommended action:**", r.recommended_action)
                        if r.requires_structural_engineer:
                            st.error("Structural engineer inspection recommended.")
                        st.download_button("Download JSON", r.model_dump_json(indent=2), "crack_report.json")

# --------------------------------------------------------------- estimation
with tab_est:
    st.subheader("Material & cost estimation")
    if "area" not in st.session_state:
        st.session_state["area"] = 1500
        st.session_state["floors"] = 1
    plan = st.file_uploader("Optional: upload a floor plan to auto-fill area and floors",
                            type=["png", "jpg", "jpeg", "webp"], key="plan_file")
    if plan and st.button("Extract from plan"):
        client = need_ai()
        imgs = read_images([plan])
        if client and imgs:
            p = run_ai(extract_plan_details, client, imgs[0])
            if p:
                if p.built_up_area_sqft > 0:
                    st.session_state["area"] = int(p.built_up_area_sqft)
                if p.floors > 0:
                    st.session_state["floors"] = p.floors
                st.info(f"Extracted: {p.built_up_area_sqft:.0f} sq ft, {p.floors} floor(s). {p.notes}")
    c1, c2, c3, c4 = st.columns(4)
    area = c1.number_input("Total built-up area (sq ft)", 100, 1_000_000, step=50, key="area")
    floors = c2.number_input("Floors", 1, 50, key="floors")
    quality = c3.selectbox("Quality", QUALITIES, index=1)
    wastage = c4.slider("Wastage %", 0, 15, 5)
    finishing = st.checkbox("Include finishing (flooring, paint, fittings)")
    mats = estimate_materials(area, floors, quality, wastage)
    cost = estimate_cost(mats, area, quality, finishing)

    st.dataframe(pd.DataFrame([{"Item": l.item, "Quantity": f"{l.quantity:,.0f} {l.unit}",
                                "Rate": format_inr(l.rate), "Amount": format_inr(l.amount)}
                               for l in cost.material_lines]), use_container_width=True, hide_index=True)
    rows = [("Materials", cost.material_total), ("Labour", cost.labour)]
    if finishing:
        rows.append(("Finishing", cost.finishing))
    rows += [("Overhead", cost.overhead), ("Contingency", cost.contingency),
             ("Subtotal", cost.subtotal), ("GST", cost.gst), ("Grand total", cost.grand_total)]
    st.dataframe(pd.DataFrame([{"Component": k, "Amount": format_inr(v)} for k, v in rows]),
                 use_container_width=True, hide_index=True)
    m1, m2 = st.columns(2)
    m1.metric("Estimated project cost", format_inr(cost.grand_total))
    m2.metric("Cost per sq ft", format_inr(cost.per_sqft))
    st.caption("Preliminary thumb-rule estimate (about ±15–20%). Edit `construction_ai/data/*.json` for local rates.")
    st.download_button("Download estimate (CSV)", pd.DataFrame(
        [{"Component": k, "Amount_INR": round(v)} for k, v in rows]).to_csv(index=False), "estimate.csv")

# ----------------------------------------------------------------- schedule
with tab_sched:
    st.subheader("Task scheduling & critical path")
    start = st.date_input("Project start", date.today())
    use_weather = st.checkbox("Block rain/storm 'stop' days from the weather tab",
                              disabled="forecast" not in st.session_state)
    seed = pd.DataFrame([{"id": t.id, "name": t.name, "duration_days": t.duration_days,
                          "depends_on": ",".join(t.depends_on)} for t in default_residential_tasks()])
    edited = st.data_editor(seed, num_rows="dynamic", use_container_width=True, key="task_editor")
    try:
        tasks = [Task(str(r.id).strip(), str(r.name), int(r.duration_days),
                      tuple(x.strip() for x in str(r.depends_on or "").split(",") if x.strip()))
                 for r in edited.itertuples() if str(r.id).strip() and str(r.id) != "nan"]
        blocked = rain_stop_dates(st.session_state["forecast"]) if use_weather else set()
        sched = build_schedule(tasks, start, blocked_dates=blocked)
        finish = project_finish(sched)
        a, b = st.columns(2)
        a.metric("Planned finish", finish.strftime("%d %b %Y"))
        b.metric("Critical tasks", sum(s.critical for s in sched))
        df = pd.DataFrame([{"Task": f"{s.id} {s.name}", "Start": pd.Timestamp(s.start),
                            "End": pd.Timestamp(s.end) + pd.Timedelta(days=1),
                            "Critical": "Critical" if s.critical else "Has slack"} for s in sched])
        st.altair_chart(alt.Chart(df).mark_bar().encode(
            x=alt.X("Start:T", title=None), x2="End:T",
            y=alt.Y("Task:N", sort=None, title=None),
            color=alt.Color("Critical:N", scale=alt.Scale(domain=["Critical", "Has slack"], range=["#DC2626", "#9CA3AF"])),
        ).properties(height=30 * len(df) + 40), use_container_width=True)
        st.dataframe(pd.DataFrame([{"ID": s.id, "Task": s.name, "Start": s.start, "End": s.end,
                                    "Slack (days)": s.slack_days, "Critical": s.critical} for s in sched]),
                     use_container_width=True, hide_index=True)
        st.session_state["schedule"] = sched
    except (ScheduleError, ValueError) as exc:
        st.error(f"Schedule problem: {exc}")

# ---------------------------------------------------------------- assistant
with tab_chat:
    st.subheader("Construction chatbot")
    if "bot" not in st.session_state:
        st.session_state["bot"] = None
    client = get_client()
    if client is None:
        st.warning("Add a Gemini key to use the chatbot and daily briefing.")
    else:
        bot = st.session_state["bot"]
        if bot is None or bot.client is not client:
            bot = ConstructionChatbot(client)
            st.session_state["bot"] = bot
        bot.project_context = f"Project: {project_name}. Location: {city}, India."
        for role, text in bot.history:
            with st.chat_message(role):
                st.markdown(text)
        if q := st.chat_input("Ask about materials, methods, IS codes, costs..."):
            with st.chat_message("user"):
                st.markdown(q)
            try:
                with st.spinner("Thinking..."):
                    ans = bot.ask(q)
                with st.chat_message("assistant"):
                    st.markdown(ans)
            except GeminiError as exc:
                st.error(str(exc))
        if st.button("Clear chat"):
            bot.reset()
            st.rerun()

    st.divider()
    st.subheader("Daily site assistant")
    log = st.text_area("Yesterday's site log / issues", height=120,
                       placeholder="e.g. Slab shuttering 80% done, cement stock low, 2 masons absent...")
    if st.button("Generate today's briefing", type="primary"):
        client = need_ai()
        if client:
            today = date.today()
            todays = [f"{s.id} {s.name}" for s in st.session_state.get("schedule", [])
                      if s.start <= today <= s.end]
            wx = []
            if "forecast" in st.session_state:
                match = [f for f in st.session_state["forecast"] if f.day == today]
                if match:
                    wx = assess_day(match[0]).messages
            br = run_ai(generate_daily_briefing, client, log, todays, wx)
            if br:
                st.markdown(f"### {br.headline}")
                for title, items in [("Priorities", br.priorities), ("Safety focus", br.safety_focus),
                                     ("Material & equipment checks", br.material_and_equipment_checks),
                                     ("Weather", br.weather_considerations), ("Risks", br.risks),
                                     ("End-of-day checklist", br.end_of_day_checklist)]:
                    st.markdown(f"**{title}**")
                    st.markdown("\n".join(f"- {i}" for i in items) or "- none")
                st.write("**Manpower:**", br.manpower_notes)

# ------------------------------------------------------------------ weather
with tab_weather:
    st.subheader("7-day weather advisory")
    place = st.text_input("Location", city, key="wx_place")
    if st.button("Get forecast", type="primary"):
        try:
            with st.spinner("Fetching forecast..."):
                lat, lon, label = geocode(place)
                st.session_state["forecast"] = fetch_forecast(lat, lon)
                st.session_state["forecast_label"] = label
        except WeatherError as exc:
            st.error(str(exc))
    if "forecast" in st.session_state:
        st.caption(f"Forecast for {st.session_state.get('forecast_label', place)}")
        for f in st.session_state["forecast"]:
            adv = assess_day(f)
            with st.expander(f"{LEVEL_ICON[adv.level]} {f.day:%a %d %b}: {f.temp_min_c:.0f}–{f.temp_max_c:.0f} °C, "
                             f"rain {f.rain_mm:.1f} mm ({f.rain_prob_pct:.0f}%), wind {f.wind_max_kmh:.0f} km/h",
                             expanded=adv.level != "ok"):
                for m in adv.messages:
                    st.write("•", m)
