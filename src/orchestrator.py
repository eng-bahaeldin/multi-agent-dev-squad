from datetime import datetime, timezone
from typing import Any, Callable, Optional
from langgraph.graph import END, START, StateGraph
from src.agents.coder_agent import run_coder_agent
from src.agents.reviewer_agent import run_reviewer_agent
from src.agents.spec_agent import run_spec_agent
from src.schemas import CodeArtifact, QAReport, SpecArtifact, SquadState

DEFAULT_MAX_ITERATIONS: int = 4


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S UTC")


def build_squad_graph(
    spec_fn: Optional[Callable[[str], SpecArtifact]] = None,
    coder_fn: Optional[Callable[..., CodeArtifact]] = None,
    reviewer_fn: Optional[Callable[..., QAReport]] = None,
):
    exec_spec = spec_fn or run_spec_agent
    exec_coder = coder_fn or run_coder_agent
    exec_reviewer = reviewer_fn or run_reviewer_agent

    def spec_node(state: SquadState) -> dict[str, Any]:
        spec = exec_spec(state["user_request"])
        events = list(state.get("timeline", []))
        events.append({"time": _ts(), "agent": "Spec Agent", "status": "SPEC_READY", "detail": spec.feature_name})
        return {"spec": spec, "iteration": 0, "timeline": events}

    def coder_node(state: SquadState) -> dict[str, Any]:
        next_iter = int(state.get("iteration", 0)) + 1
        code = exec_coder(
            spec=state["spec"],
            iteration=next_iter,
            previous_code=state.get("code"),
            latest_qa=state.get("qa_report"),
            inject_bug=bool(state.get("inject_bug", False)),
        )
        events = list(state.get("timeline", []))
        events.append({"time": _ts(), "agent": "Coder Agent", "status": f"BUILD_V{next_iter}", "detail": f"Generated solution.py & tests (cycle {next_iter})"})
        return {"code": code, "iteration": next_iter, "timeline": events}

    def reviewer_node(state: SquadState) -> dict[str, Any]:
        max_iter = int(state.get("max_iterations", DEFAULT_MAX_ITERATIONS))
        report = exec_reviewer(spec=state["spec"], code=state["code"], max_iterations=max_iter)
        events = list(state.get("timeline", []))
        events.append({"time": _ts(), "agent": "Reviewer/QA Agent", "status": report.status, "detail": f"{report.total_tests - report.failed_tests}/{report.total_tests} passed"})
        return {"qa_report": report, "timeline": events}

    def route_after_qa(state: SquadState) -> str:
        report = state.get("qa_report")
        cur_iter = int(state.get("iteration", 1))
        max_iter = int(state.get("max_iterations", DEFAULT_MAX_ITERATIONS))
        if report is not None and report.tests_passed:
            return END
        if cur_iter >= max_iter or (report is not None and report.status == "MAX_CYCLES_EXCEEDED"):
            return END
        return "coder_node"

    builder = StateGraph(SquadState)
    builder.add_node("spec_node", spec_node)
    builder.add_node("coder_node", coder_node)
    builder.add_node("reviewer_node", reviewer_node)
    builder.add_edge(START, "spec_node")
    builder.add_edge("spec_node", "coder_node")
    builder.add_edge("coder_node", "reviewer_node")
    builder.add_conditional_edges("reviewer_node", route_after_qa, {"coder_node": "coder_node", END: END})
    return builder.compile()


def run_squad(user_request: str, max_iterations: int = DEFAULT_MAX_ITERATIONS, inject_bug: bool = False) -> SquadState:
    graph = build_squad_graph()
    initial_state: SquadState = {
        "user_request": user_request,
        "iteration": 0,
        "max_iterations": max_iterations,
        "inject_bug": inject_bug,
        "timeline": [],
    }
    return graph.invoke(initial_state)
