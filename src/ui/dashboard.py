"""
ClaimRecon AI — Streamlit Investigator Dashboard
Section 17 of the blueprint.

Run with:
    streamlit run src/ui/dashboard.py
"""

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

import json
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Allow imports from project root when running via streamlit
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.graph import build_graph


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
</style>
""", unsafe_allow_html=True)


# ─── Sidebar — package selector ───────────────────────────────────────────────
st.sidebar.title("🔍 ClaimRecon AI")
st.sidebar.markdown("---")

PACKAGES = {
    "✅ Complete Package (CLM-2026-0042)":
        "data/complete_claim_package_clm_2026_0042",
    "⚠️  Incomplete Package (CLM-2026-0042)":
        "data/incomplete_claim_package_clm_2026_0042",
}

selected_label = st.sidebar.selectbox(
    "Select Claim Package",
    list(PACKAGES.keys()),
    index=0,
)
selected_folder = PACKAGES[selected_label]

st.sidebar.markdown("---")
st.sidebar.markdown("**LLM Provider:**")
provider = os.getenv("LLM_PROVIDER", "gemini").upper()
model = os.getenv("LLM_MODEL", "gemini-2.0-flash")
st.sidebar.code(f"{provider}\n{model}", language=None)

run_button = st.sidebar.button("▶  Run Analysis", use_container_width=True, type="primary")

st.sidebar.markdown("---")
st.sidebar.markdown(
    "💡 Switch packages above and re-run to compare complete vs. incomplete claim packages."
)

# ─── Session state ─────────────────────────────────────────────────────────────
if "result" not in st.session_state:
    st.session_state.result = None
if "last_folder" not in st.session_state:
    st.session_state.last_folder = None

# ─── Run pipeline ─────────────────────────────────────────────────────────────
if run_button:
    with st.spinner("Running ClaimRecon AI pipeline…"):
        try:
            graph = build_graph()
            result = graph.invoke({"claim_folder": selected_folder})
            st.session_state.result = result
            st.session_state.last_folder = selected_folder
        except Exception as e:
            st.error(f"Pipeline error: {e}")
            st.stop()

# ─── Main content ─────────────────────────────────────────────────────────────
if st.session_state.result is None:
    # Landing screen
    st.title("ClaimRecon AI")
    st.markdown(
        "#### Bounded Agentic Claim-Package Validation & Supported-Amount Analysis"
    )
    st.info(
        "Select a claim package from the sidebar and click **▶ Run Analysis** to begin.",
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

# ─── Header banner ────────────────────────────────────────────────────────────
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

# ─── KPI Metrics ──────────────────────────────────────────────────────────────
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

# ─── Invariant check ─────────────────────────────────────────────────────────
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

# ─── Two-column layout ────────────────────────────────────────────────────────
left_col, right_col = st.columns([3, 2])

# ─── Left: Integrity Findings ────────────────────────────────────────────────
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

# ─── Right: Package Status & Summary ─────────────────────────────────────────
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

# ─── Execution Trace (collapsed) ─────────────────────────────────────────────
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
        # Show a clean subset of state (not raw documents)
        clean_state = {
            "run_id": result.get("run_id"),
            "status": result.get("status"),
            "claim": result.get("claim"),
            "check_evaluation": result.get("check_evaluation"),
            "financial_summary": result.get("financial_summary"),
            "investigator_summary": result.get("investigator_summary"),
        }
        st.json(clean_state)

