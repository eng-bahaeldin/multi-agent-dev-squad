import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from src.orchestrator import DEFAULT_MAX_ITERATIONS, run_squad

st.set_page_config(page_title="3-Agent Dev Squad & QA Convergence", layout="wide")

if "squad_result" not in st.session_state:
    st.session_state.squad_result = None
if "running" not in st.session_state:
    st.session_state.running = False

with st.sidebar:
    st.header("Squad Governance & Telemetry")
    max_cycles = st.number_input("Max Refinement Cycles", min_value=1, max_value=6, value=DEFAULT_MAX_ITERATIONS)
    inject_bug = st.toggle("Adversarial Bug Injection (Pass 1)", value=False, help="Forces Coder Agent to inject a subtle logic flaw on iteration 1 to demonstrate QA self-healing.")
    st.divider()
    res = st.session_state.squad_result
    cur_iter = res.get("iteration", 0) if res else 0
    qa = res.get("qa_report") if res else None
    st.metric("Iteration Depth", f"Iteration {cur_iter} / {max_cycles}")
    if st.session_state.running:
        st.warning("Status: IN PROGRESS")
    elif qa is not None and qa.tests_passed:
        st.success("Status: CONVERGED (ALL TESTS PASS)")
    elif qa is not None:
        st.error(f"Status: TERMINATED ({qa.status})")
    else:
        st.info("Status: IDLE (READY)")
    st.divider()
    st.caption("Sandbox Policy: shell=False | TemporaryDirectory | 10s Timeout | Env Scrubbed")

st.title("Autonomous 3-Agent Software Development Squad")
st.caption("Product Spec Agent -> Coder Agent -> Deterministic Sandboxed Reviewer/QA Agent")

p1, p2 = st.columns(2)
default_prompt = (
    "Build a robust Python rate-limiting class using the Token Bucket algorithm with thread-safety, "
    "microsecond precision, burst allowance, and refill rate calculation."
)
if "draft_prompt" not in st.session_state:
    st.session_state.draft_prompt = default_prompt
with p1:
    if st.button("Preset 1: Token Bucket Rate Limiter", use_container_width=True):
        st.session_state.draft_prompt = default_prompt
        st.rerun()
with p2:
    if st.button("Preset 2: Thread-Safe LRU Cache with TTL", use_container_width=True):
        st.session_state.draft_prompt = (
            "Build a thread-safe LRUCache class in Python with max_size capacity, per-entry TTL expiration "
            "in seconds using time.monotonic(), get(key), put(key, value), and expired entry eviction."
        )
        st.rerun()

user_req = st.text_area("Product Feature / Algorithmic Specification Request:", value=st.session_state.draft_prompt, height=100)
if st.button("Execute 3-Agent Development Squad", type="primary", use_container_width=True):
    if not user_req.strip():
        st.warning("Please enter a feature request first.")
    else:
        st.session_state.running = True
        try:
            with st.spinner("Running Spec -> Coder -> Sandboxed QA convergence loop..."):
                output = run_squad(user_request=user_req.strip(), max_iterations=int(max_cycles), inject_bug=inject_bug)
            st.session_state.squad_result = output
        except Exception as exc:
            st.error(f"Squad execution failed: {exc}")
        finally:
            st.session_state.running = False
        st.rerun()

res = st.session_state.squad_result
if res:
    st.subheader("Multi-Agent Collaboration Timeline")
    timeline = res.get("timeline", [])
    if timeline:
        cols = st.columns(len(timeline))
        for idx, ev in enumerate(timeline):
            with cols[idx]:
                st.info(f"**{ev.get('agent', '')}**\n`{ev.get('status', '')}`\n{ev.get('detail', '')}")

    spec = res.get("spec")
    code = res.get("code")
    qa = res.get("qa_report")

    tab_spec, tab_coder, tab_qa = st.tabs(["Spec Board", "Coder Terminal", "QA Test Runner Console"])
    with tab_spec:
        if spec:
            st.markdown(f"### Feature: `{spec.feature_name}`")
            st.markdown("**Target Interfaces:**")
            st.code(spec.interfaces, language="python")
            c_req, c_tc = st.columns(2)
            with c_req:
                st.markdown("**Architectural Requirements:**")
                for r in spec.requirements:
                    st.markdown(f"- {r}")
            with c_tc:
                st.markdown("**Acceptance Test Plan:**")
                for tc in spec.test_cases:
                    st.markdown(f"- {tc}")
    with tab_coder:
        if code:
            st.markdown(f"### Build Artifact (Iteration {code.iteration})")
            st.markdown("**Implementation (`solution.py`):**")
            st.code(code.implementation_code, language="python")
            st.markdown("**Generated Pytest Suite (`test_solution.py`):**")
            st.code(code.test_code, language="python")
    with tab_qa:
        if qa:
            m1, m2, m3 = st.columns(3)
            m1.metric("Verdict", qa.status)
            m2.metric("Total Pytest Cases", qa.total_tests)
            m3.metric("Failed Cases", qa.failed_tests)
            st.markdown("**Reviewer / QA Critique Notes:**")
            for note in qa.review_feedback:
                st.markdown(f"- {note}")
            st.markdown("**Raw Sandboxed Pytest Console Output:**")
            st.code(qa.execution_output, language="text")
