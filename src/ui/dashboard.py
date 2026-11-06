"""
ClaimRecon AI — Streamlit Investigator Dashboard
Section 17 of the blueprint with Multi-Claim Portfolio Analytics and Run History Persistence.

Run with:
    streamlit run src/ui/dashboard.py
"""
from __future__ import annotations

import sys
import os
import warnings

# Suppress all deprecation, future, and runtime warnings before third-party imports
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["GRPC_VERBOSITY"] = "NONE"
warnings.filterwarnings("ignore")
try:
    from langchain_core._api.deprecation import LangChainPendingDeprecationWarning
    warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)
except Exception:
    pass

from pathlib import Path
import json
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Allow imports from project root when running via streamlit
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.graph import build_graph
from src.history import (
    save_run,
    get_latest_runs_by_claim,
    compute_portfolio_metrics,
)


# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ClaimRecon AI",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
.metric-card {
    background: #1e1e2e;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
}
.finding-header {
    font-weight: 600;
    font-size: 0.85rem;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.status-complete   { color: #4ade80; font-weight: 700; }
.status-partial    { color: #facc15; font-weight: 700; }
.status-review     { color: #f87171; font-weight: 700; }
.invariant-pass    { color: #4ade80; }
.invariant-fail    { color: #f87171; }
.claim-card {
    border: 1px solid #333;
    border-radius: 8px;
    padding: 14px;
    margin-bottom: 12px;
    background: #181825;
}
.score-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-weight: 700;
    border-radius: 12px;
    padding: 2px 8px;
    font-size: 0.8rem;
}
.score-badge-green  { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #059669; }
.score-badge-orange { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #d97706; }
.score-badge-red    { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #dc2626; }
</style>
""", unsafe_allow_html=True)


# ─── Visual circular progress helper ──────────────────────────────────────────
def render_circular_score(score_pct: float, size: int = 58) -> str:
    """
    Generate an inline SVG radial progress ring for document completeness score.
    """
    score_pct = max(0.0, min(100.0, float(score_pct)))
    # Radius & circumference
    stroke_width = 5
    radius = (size - stroke_width * 2) // 2
    circ = 2 * 3.14159 * radius
    dashoffset = circ * (1.0 - (score_pct / 100.0))

    if score_pct >= 99.5:
        color = "#10b981"  # Emerald
        bg_color = "rgba(16, 185, 129, 0.15)"
    elif score_pct >= 70.0:
        color = "#f59e0b"  # Amber
        bg_color = "rgba(245, 158, 11, 0.15)"
    else:
        color = "#ef4444"  # Red
        bg_color = "rgba(239, 68, 68, 0.15)"

    center = size // 2
    font_size = max(11, size // 4)

    return f"""
    <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" style="display:inline-block; vertical-align:middle;">
        <circle cx="{center}" cy="{center}" r="{radius}" fill="{bg_color}" stroke="#333" stroke-width="{stroke_width}" />
        <circle cx="{center}" cy="{center}" r="{radius}" fill="none" stroke="{color}" stroke-width="{stroke_width}"
                stroke-dasharray="{circ:.2f}" stroke-dashoffset="{dashoffset:.2f}" stroke-linecap="round"
                transform="rotate(-90 {center} {center})" />
        <text x="{center}" y="{center + 4}" text-anchor="middle" font-size="{font_size}" font-weight="700" fill="{color}" font-family="sans-serif">
            {int(score_pct)}%
        </text>
    </svg>
    """


# ─── Dynamic package discovery ────────────────────────────────────────────────
def discover_claim_packages(data_dir: str = "data") -> dict[str, str]:
    """Scan data directory and discover available claim packages."""
    base_path = Path(data_dir)
    if not base_path.exists():
        base_path = Path(__file__).resolve().parent.parent.parent / "data"

    if not base_path.exists():
        return {}

    packages = {}
    for p in sorted(base_path.iterdir()):
        if p.is_dir() and not p.name.startswith("."):
            folder_name = p.name
            is_incomplete = "incomplete" in folder_name.lower()
            icon = "⚠️ " if is_incomplete else "✅"
            status_text = "Incomplete Package" if is_incomplete else "Complete Package"

            claim_id = ""
            ocr_file = p / "claim_information_ocr.json"
            if ocr_file.exists():
                try:
                    with open(ocr_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        claim_id = meta.get("claim_profile", "")
                except Exception:
                    pass

            if not claim_id:
                if "clm_" in folder_name.lower():
                    suffix = folder_name.lower().split("clm_")[-1]
                    claim_id = "CLM-" + suffix.replace("_", "-").upper()
                else:
                    claim_id = folder_name

            label = f"{icon} {status_text} ({claim_id})"
            try:
                rel_path = str(p.relative_to(Path.cwd()))
            except ValueError:
                rel_path = str(p)
            packages[label] = rel_path

    return packages


# ─── Sidebar Navigation ───────────────────────────────────────────────────────
st.sidebar.title("🔍 ClaimRecon AI")
st.sidebar.markdown("---")

app_mode = st.sidebar.radio(
    "Navigation Mode",
    ["📊 Portfolio Overview", "🔍 Single Claim Investigation"],
    index=0,
)

st.sidebar.markdown("---")

PACKAGES = discover_claim_packages()
if not PACKAGES:
    PACKAGES = {
        "✅ Complete Package (CLM-2026-0042)": "data/complete_claim_package_clm_2026_0042"
    }

selected_label = st.sidebar.selectbox(
    "Select Target Package",
    list(PACKAGES.keys()),
    index=0,
)
selected_folder = PACKAGES[selected_label]

st.sidebar.markdown("---")
st.sidebar.markdown("**LLM Provider:**")
provider = os.getenv("LLM_PROVIDER", "gemini").upper()
model = os.getenv("LLM_MODEL", "gemini-3.8-flash")
st.sidebar.code(f"{provider}\n{model}", language=None)

run_button = st.sidebar.button("▶  Run Selected Analysis", use_container_width=True, type="primary")

st.sidebar.markdown("---")

# Optional batch runner button
batch_button = st.sidebar.button("⚡ Run All Packages Batch", use_container_width=True)

# ─── Session state ─────────────────────────────────────────────────────────────
if "result" not in st.session_state:
    st.session_state.result = None
if "last_folder" not in st.session_state:
    st.session_state.last_folder = None


# ─── Run Single Pipeline ──────────────────────────────────────────────────────
if run_button:
    with st.spinner("Running ClaimRecon AI pipeline…"):
        try:
            graph = build_graph()
            result = graph.invoke({"claim_folder": selected_folder})
            st.session_state.result = result
            st.session_state.last_folder = selected_folder
            # Automatically persist run to history
            save_run(result)
            st.toast(f"✅ Run saved to history for {result.get('claim', {}).get('claim_profile', '')}")
        except Exception as e:
            st.error(f"Pipeline error: {e}")
            st.stop()


# ─── Run All Packages in Batch ────────────────────────────────────────────────
if batch_button:
    progress_bar = st.progress(0, text="Initializing batch run…")
    total_pkgs = len(PACKAGES)
    completed_count = 0
    graph = build_graph()

    for idx, (lbl, fpath) in enumerate(PACKAGES.items()):
        progress_bar.progress((idx) / total_pkgs, text=f"Analyzing {lbl}…")
        try:
            res = graph.invoke({"claim_folder": fpath})
            save_run(res)
            completed_count += 1
        except Exception as err:
            st.warning(f"Error analyzing {lbl}: {err}")

    progress_bar.progress(1.0, text="Batch analysis complete!")
    st.success(f"Successfully evaluated and logged {completed_count}/{total_pkgs} claim packages!")


# ==============================================================================
# VIEW 1: PORTFOLIO OVERVIEW
# ==============================================================================
if app_mode == "📊 Portfolio Overview":
    st.title("📊 Multi-Claim Portfolio Overview")
    st.markdown("Aggregated loss validation, supported amounts, and cross-account findings across historical evaluations.")
    st.markdown("---")

    latest_runs = get_latest_runs_by_claim()
    portfolio = compute_portfolio_metrics(latest_runs)

    # ── KPI Metrics Ribbon ────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Submitted / Claimed",
            f"${portfolio['total_claimed']:,.2f}",
            help="Total claimed stock value across all evaluated claims",
        )

    with col2:
        st.metric(
            "Total Supported Amount",
            f"${portfolio['total_supported']:,.2f}",
            delta=(
                f"{(portfolio['total_supported'] / portfolio['total_claimed'] * 100):.1f}% supported"
                if portfolio['total_claimed'] > 0 else None
            ),
            delta_color="normal",
            help="Verified claim amounts from fully completed integrity checks",
        )

    with col3:
        st.metric(
            "Total Unsupported Amount",
            f"${portfolio['total_unsupported']:,.2f}",
            delta=(
                f"{(portfolio['total_unsupported'] / portfolio['total_claimed'] * 100):.1f}% unsupported"
                if portfolio['total_claimed'] > 0 else None
            ),
            delta_color="inverse",
            help="Deductions identified across duplicate, post-loss delivery, and amount mismatches",
        )

    with col4:
        st.metric(
            "Accounts Evaluated",
            f"{portfolio['total_claims_evaluated']} claims",
            delta=f"{portfolio['total_findings_count']} total findings",
            delta_color="off",
        )

    st.markdown("---")

    if not portfolio["claims"]:
        st.info("No claim evaluations found in history. Select a package and click **▶ Run Selected Analysis** (or **⚡ Run All Packages Batch**) to populate this dashboard.")
    else:
        # ── Controls for Sorting Claims ───────────────────────────────────────
        sort_col1, sort_col2 = st.columns([2, 3])
        with sort_col1:
            sort_by = st.selectbox(
                "Sort claims by:",
                [
                    "Claimed Amount (Descending)",
                    "Unsupported Amount (Descending)",
                    "Document Completion (Lowest First - Needs Attention)",
                    "Findings Count (Descending)",
                    "Loss Date (Newest First)",
                ],
                index=0,
            )

        claims_list = list(portfolio["claims"])
        if sort_by == "Claimed Amount (Descending)":
            claims_list.sort(key=lambda c: c["claimed_amount"], reverse=True)
        elif sort_by == "Unsupported Amount (Descending)":
            claims_list.sort(key=lambda c: c["unsupported_amount"], reverse=True)
        elif sort_by == "Document Completion (Lowest First - Needs Attention)":
            claims_list.sort(key=lambda c: c.get("completeness_pct", 100.0))
        elif sort_by == "Findings Count (Descending)":
            claims_list.sort(key=lambda c: c["findings_count"], reverse=True)
        elif sort_by == "Loss Date (Newest First)":
            claims_list.sort(key=lambda c: c.get("loss_date", ""), reverse=True)

        st.subheader("📋 Evaluated Claims Leaderboard")
        st.caption("Click any claim card below to expand and view specific findings, evidence, and amounts.")

        # ── Claims Cards with Expandable Findings ─────────────────────────────
        for idx, claim in enumerate(claims_list, 1):
            is_complete = claim["calculation_complete"]
            comp_score = float(claim.get("completeness_pct", 100.0))

            # Score badge in expander header
            if comp_score >= 99.5:
                badge_tag = f"🟢 {int(comp_score)}% Docs"
            elif comp_score >= 70.0:
                badge_tag = f"🟠 {int(comp_score)}% Docs"
            else:
                badge_tag = f"🔴 {int(comp_score)}% Docs"

            status_badge = "✅ Fully Supported/Evaluated" if is_complete else "⚠️ Partial Result (Checks Blocked)"
            supported_str = f"${claim['supported_amount']:,.2f}" if claim["supported_amount"] is not None else "N/A (Incomplete)"

            header_title = (
                f"#{idx}  [{badge_tag}]  **{claim['claim_profile']}** — {claim['insured']}  |  "
                f"Claimed: **${claim['claimed_amount']:,.2f}**  |  "
                f"Unsupported: **${claim['unsupported_amount']:,.2f}**  |  "
                f"{claim['findings_count']} Finding(s)"
            )

            with st.expander(header_title, expanded=(idx == 1)):
                # Summary header row with circular progress gauge
                c_gauge, c1, c2, c3, c4 = st.columns([1.2, 2.5, 2.5, 2.5, 1.8])

                with c_gauge:
                    st.markdown("**Docs Score**")
                    st.markdown(render_circular_score(comp_score, size=64), unsafe_allow_html=True)

                with c1:
                    st.markdown(f"**Loss Date:** `{claim['loss_date']}`")
                    st.markdown(f"**Evaluation Status:** {status_badge}")
                with c2:
                    st.markdown(f"**Claimed Amount:** `${claim['claimed_amount']:,.2f}`")
                    st.markdown(f"**Supported Amount:** `{supported_str}`")
                with c3:
                    st.markdown(f"**Unsupported Amount:** `${claim['unsupported_amount']:,.2f}`")
                    st.markdown(f"**Findings Count:** `{claim['findings_count']}`")
                with c4:
                    if st.button(f"🔍 Deep Dive", key=f"load_dive_{claim['claim_profile']}_{idx}"):
                        st.session_state.result = claim["raw_record"]
                        st.session_state.last_folder = claim["raw_record"].get("claim_folder")
                        st.toast(f"Loaded {claim['claim_profile']} into Single Claim Investigation tab!")

                # Missing Documents Alert Banner inside the card if incomplete
                missing = claim.get("missing_docs", [])
                if missing:
                    st.warning(
                        f"⚠️ **Incomplete Document Package ({comp_score:.0f}% Complete)** — "
                        f"Missing required file(s): `{', '.join(missing)}`. "
                        "Post-loss integrity check is blocked.",
                        icon="⚠️",
                    )
                else:
                    st.caption("✅ All required claim checklist documents verified present.")

                # Findings drill-down
                findings = claim.get("findings", [])
                st.markdown("#### 🔍 Integrity Findings for this Account")
                if not findings:
                    st.success("No anomalies or unsupported deductions identified for this claim.")
                else:
                    for f in findings:
                        rule_name = f.get("rule_id", "").replace("_V1", "").replace("_", " ").title()
                        f_impact = float(f.get("financial_impact", 0))
                        st.markdown(
                            f"- **{f.get('finding_id')}** [{rule_name}] — Invoice `{f.get('claim_line_key')}`: "
                            f"**-${f_impact:,.2f}** ({f.get('financial_treatment')})"
                        )
                        st.caption(f"&nbsp;&nbsp;&nbsp;&nbsp;{f.get('description', '')}")
                        evidence_items = f.get("evidence", [])
                        if evidence_items:
                            st.caption(f"&nbsp;&nbsp;&nbsp;&nbsp;*Evidence Sources:* {', '.join(evidence_items)}")

                # Executive summary narrative if present
                exec_summary = claim.get("summary", {}).get("executive_summary")
                if exec_summary:
                    st.markdown("**Investigator Note:**")
                    st.info(exec_summary)


# ==============================================================================
# VIEW 2: SINGLE CLAIM INVESTIGATION
# ==============================================================================
elif app_mode == "🔍 Single Claim Investigation":
    # ── Claim selector dropdown at the top of Single Claim view ───────────────
    top_col1, top_col2 = st.columns([3, 1])

    with top_col1:
        # Build selector options from discovered packages
        pkg_options = list(PACKAGES.keys())
        # Find default index based on current session_state or target
        current_idx = 0
        if st.session_state.last_folder:
            for i, opt in enumerate(pkg_options):
                if PACKAGES[opt] == st.session_state.last_folder:
                    current_idx = i
                    break

        claim_selected = st.selectbox(
            "📁 Select Claim Package to Investigate:",
            pkg_options,
            index=current_idx,
            key="single_claim_selector",
        )
        chosen_folder = PACKAGES[claim_selected]

    with top_col2:
        st.write("")  # align vertically
        st.write("")
        run_current = st.button("▶ Run / Re-evaluate", use_container_width=True, type="primary", key="btn_run_single_top")

    # If the user selects a different claim package or clicks Run, execute or load
    if run_current or (st.session_state.last_folder != chosen_folder and st.session_state.result is None):
        with st.spinner(f"Running ClaimRecon AI pipeline on {claim_selected}…"):
            try:
                graph = build_graph()
                result = graph.invoke({"claim_folder": chosen_folder})
                st.session_state.result = result
                st.session_state.last_folder = chosen_folder
                save_run(result)
                st.toast(f"✅ Evaluated {result.get('claim', {}).get('claim_profile', '')}")
            except Exception as e:
                st.error(f"Pipeline error: {e}")
                st.stop()
    elif st.session_state.last_folder != chosen_folder and st.session_state.result is not None:
        # Check if we already have a historical run for this chosen folder
        latest_runs = get_latest_runs_by_claim()
        found_hist = None
        for hr in latest_runs:
            if hr.get("claim_folder") == chosen_folder:
                found_hist = hr
                break

        if found_hist:
            st.session_state.result = found_hist
            st.session_state.last_folder = chosen_folder
        else:
            # Need to run
            with st.spinner(f"Analyzing {claim_selected}…"):
                try:
                    graph = build_graph()
                    result = graph.invoke({"claim_folder": chosen_folder})
                    st.session_state.result = result
                    st.session_state.last_folder = chosen_folder
                    save_run(result)
                except Exception as e:
                    st.error(f"Pipeline error: {e}")
                    st.stop()

    if st.session_state.result is None:
        st.title("ClaimRecon AI")
        st.markdown(
            "#### Bounded Agentic Claim-Package Validation & Supported-Amount Analysis"
        )
        st.info(
            "Select a claim package from the sidebar and click **▶ Run Selected Analysis** to begin, or switch to **📊 Portfolio Overview** to see cross-claim metrics.",
            icon="ℹ️",
        )
        st.markdown("""
        **What this system does:**
        - 📄 Classifies submitted claim documents (LLM)
        - ✅ Validates package completeness against the business checklist
        - 🤖 Supervisor selects applicable integrity checks (LLM)
        - 🔍 Runs deterministic duplicate, post-loss, and mismatch checks
        - 💰 Calculates supported vs. unsupported claim amounts (Python Decimal)
        - 📝 Generates an investigator summary (LLM)
        """)
        st.stop()

    result = st.session_state.result

    claim       = result.get("claim", {})
    fs          = result.get("financial_summary", {})
    ce          = result.get("check_evaluation", {})
    findings    = result.get("integrity_findings", [])
    summary     = result.get("investigator_summary", {})
    plan        = result.get("supervisor_plan", {})
    docs        = result.get("documents", {})
    complete_r  = result.get("completeness_result", {})
    status      = result.get("status", "")

    # ── Header banner ────────────────────────────────────────────────────────────
    status_class = (
        "status-complete" if fs.get("calculation_complete") else
        "status-partial" if status == "PARTIALLY_COMPLETED" else
        "status-review"
    )
    status_label = (
        "Ready for Review" if fs.get("calculation_complete") else
        "Partial Result — Missing Documents" if status == "PARTIALLY_COMPLETED" else
        "Processing Review Required"
    )

    st.markdown(
        f"## 🔍 ClaimRecon AI &nbsp;·&nbsp; {claim.get('claim_profile', '')} "
        f"&nbsp;·&nbsp; <span class='{status_class}'>{status_label}</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"**Insured:** {claim.get('insured', '')} &nbsp;·&nbsp; "
        f"**Loss Date:** {claim.get('loss_date', '')} &nbsp;·&nbsp; "
        f"**Package:** `{st.session_state.last_folder}`"
    )
    st.markdown("---")

    # ── KPI Metrics ──────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Claimed Amount",
            f"${float(fs.get('claimed_amount', 0)):,.0f}",
            delta=None,
        )

    with col2:
        if fs.get("calculation_complete") and fs.get("supported_amount"):
            sup_val = float(fs["supported_amount"])
            st.metric(
                "Supported Amount",
                f"${sup_val:,.0f}",
                delta=f"{fs.get('supported_pct', 0):.1f}% of claimed",
                delta_color="normal",
            )
        else:
            st.metric("Supported Amount", "N/A", delta="Incomplete checks")

    with col3:
        unsup_key = (
            "unsupported_amount" if fs.get("calculation_complete")
            else "identified_unsupported_amount"
        )
        unsup_val = fs.get(unsup_key)
        if unsup_val:
            label = "Unsupported" if fs.get("calculation_complete") else "Identified Unsupported"
            st.metric(
                label,
                f"${float(unsup_val):,.0f}",
                delta=f"{fs.get('unsupported_pct', 0):.1f}% of claimed" if fs.get("calculation_complete") else "Partial",
                delta_color="inverse",
            )
        else:
            st.metric("Unsupported Amount", "$0")

    with col4:
        cs = ce.get("check_summary", {})
        checks_str = (
            f"{cs.get('completed', 0)}✅ "
            f"{cs.get('blocked', 0)}⚠️ "
            f"{cs.get('failed', 0)}❌"
        )
        st.metric(
            "Checks",
            checks_str,
            delta=f"of {cs.get('configured', 0)} configured",
            delta_color="off",
        )

    # ── Invariant check ─────────────────────────────────────────────────────────
    if fs.get("calculation_complete"):
        claimed = float(fs.get("claimed_amount", 0))
        supported = float(fs.get("supported_amount", 0))
        unsupported = float(fs.get("unsupported_amount", 0))
        ok = abs((supported + unsupported) - claimed) < 0.01
        inv_msg = (
            f"✅ Financial Invariant: {supported:,.2f} + {unsupported:,.2f} = {supported+unsupported:,.2f}  (**PASSES**)"
            if ok else
            f"❌ Financial Invariant FAILED: {supported:,.2f} + {unsupported:,.2f} ≠ {claimed:,.2f}"
        )
        st.markdown(f"<small class='{'invariant-pass' if ok else 'invariant-fail'}'>{inv_msg}</small>", unsafe_allow_html=True)

    st.markdown("---")

    # ── Two-column layout ────────────────────────────────────────────────────────
    left_col, right_col = st.columns([3, 2])

    # ── Left: Integrity Findings ────────────────────────────────────────────────
    with left_col:
        st.subheader("🔍 Integrity Findings")

        if not findings:
            st.info("No integrity findings identified.")
        else:
            for f in findings:
                rule_label = f.get("rule_id", "").replace("_V1", "").replace("_", " ").title()
                inv = f.get("claim_line_key", "")
                impact = float(f.get("financial_impact", 0))

                with st.expander(
                    f"**{f.get('finding_id')}** · {rule_label} · {inv} · ${impact:,.0f}",
                    expanded=False,
                ):
                    cols = st.columns(2)
                    with cols[0]:
                        st.markdown(f"**Rule:** `{f.get('rule_id')}`")
                        st.markdown(f"**Invoice:** `{inv}`")
                        st.markdown(f"**Treatment:** `{f.get('financial_treatment')}`")
                        st.markdown(f"**Impact:** **${impact:,.2f}**")

                    with cols[1]:
                        st.markdown("**Facts:**")
                        facts = f.get("facts", {})
                        for k, v in facts.items():
                            st.markdown(f"- `{k}`: {v}")

                    st.markdown("**Description:**")
                    st.info(f.get("description", ""))

                    st.markdown("**Evidence Sources:**")
                    for ev in f.get("evidence", []):
                        st.code(ev)

        # ── Partial result warning ─────────────────────────────────────────────
        if not fs.get("calculation_complete"):
            st.warning(
                f"⚠️ {fs.get('reason', 'Some checks were blocked. Results are partial.')}\n\n"
                + "\n".join(f"- `{b}`" for b in fs.get("blocked_checks", [])),
                icon="⚠️",
            )

    # ── Right: Package Status & Summary ─────────────────────────────────────────
    with right_col:
        st.subheader("📋 Package Completeness")
        completeness_pct = complete_r.get("completeness_pct", 0)
        st.progress(int(completeness_pct) / 100, text=f"{completeness_pct:.0f}% complete")

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Present:**")
            for d in complete_r.get("present_required", []):
                st.markdown(f"✅ `{d}`")
        with col_b:
            st.markdown("**Missing:**")
            missing = complete_r.get("missing_documents", [])
            if missing:
                for d in missing:
                    st.markdown(f"❌ `{d}`")
            else:
                st.markdown("_None_")

        optional_docs = [k for k in docs.keys() if k not in complete_r.get("required_documents", [])]
        if optional_docs:
            st.markdown("**Optional / Extra:**")
            for d in optional_docs:
                st.markdown(f"📎 `{d}`")

        st.markdown("---")
        st.subheader("📝 Investigator Summary")

        if summary:
            st.markdown(f"**{summary.get('executive_summary', '')}**")
            st.markdown("**Recommended Actions:**")
            for i, action in enumerate(summary.get("recommended_actions", []), 1):
                st.markdown(f"{i}. {action}")
            st.caption(f"_{summary.get('disclaimer', '')}_")
            if summary.get("generated_by") == "fallback_template":
                st.caption("⚠️ Summary generated from fallback template (LLM unavailable)")
        else:
            st.info("Summary not yet generated.")

    # ── Execution Trace (collapsed) ─────────────────────────────────────────────
    st.markdown("---")
    with st.expander("🔧 Execution Trace — Supervisor Plan & Classification Details"):
        tab1, tab2, tab3, tab4 = st.tabs(
            ["Supervisor Plan", "Document Classifications", "Completed Checks", "Raw State"]
        )

        with tab1:
            if plan:
                st.markdown(f"**Iteration:** {plan.get('iteration', 0) + 1}")
                st.markdown("**Selected Tools:**")
                for t in plan.get("selected_tools", []):
                    st.markdown(f"- ✅ `{t.get('tool')}` — {t.get('reason', '')}")
                st.markdown("**Blocked Tools:**")
                for t in plan.get("blocked_tools", []):
                    st.markdown(f"- ⚠️ `{t.get('tool')}` — {t.get('reason', '')}")
                st.markdown("**Approved (post-validation):**")
                for t in plan.get("approved_tools", []):
                    st.markdown(f"- ✅ `{t}`")
            else:
                st.info("No supervisor plan available.")

        with tab2:
            classifications = result.get("document_classifications", [])
            for cls in classifications:
                icon = "✅" if cls.get("validation_status") == "ACCEPTED" else "⚠️"
                st.markdown(
                    f"{icon} **{cls.get('filename')}** → `{cls.get('document_type')}` "
                    f"(confidence: {cls.get('confidence', 0):.0%})"
                )
                if cls.get("requires_human_review"):
                    st.caption(f"⚠️ Needs human review: {cls.get('reason', '')}")

        with tab3:
            st.markdown("**Completed Rule IDs:**")
            for rid in result.get("completed_checks", []):
                st.markdown(f"- ✅ `{rid}`")
            st.markdown("**Blocked Rule IDs:**")
            for b in result.get("blocked_checks", []):
                st.markdown(f"- ⚠️ `{b.get('rule_id')}` — {b.get('reason', '')}")
            st.markdown("**Failed Rule IDs:**")
            for f in result.get("failed_checks", []):
                st.markdown(f"- ❌ `{f.get('rule_id')}` — {f.get('error', '')}")

        with tab4:
            clean_state = {
                "run_id": result.get("run_id"),
                "status": result.get("status"),
                "claim": result.get("claim"),
                "check_evaluation": result.get("check_evaluation"),
                "financial_summary": result.get("financial_summary"),
                "investigator_summary": result.get("investigator_summary"),
            }
            st.json(clean_state)
