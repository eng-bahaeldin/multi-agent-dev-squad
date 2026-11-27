from src.agents.reviewer_agent import run_reviewer_agent
from src.orchestrator import build_squad_graph
from src.schemas import CodeArtifact, SpecArtifact


def _dummy_spec(_req: str) -> SpecArtifact:
    return SpecArtifact(
        feature_name="Adder",
        requirements=["Return sum of two integers"],
        test_cases=["test_add"],
        interfaces="def add(a: int, b: int) -> int:",
    )


def test_clean_convergence_on_iteration_one():
    calls = {"coder": 0}

    def coder_ok(spec: SpecArtifact, iteration: int, **_kw) -> CodeArtifact:
        calls["coder"] += 1
        return CodeArtifact(
            implementation_code="def add(a: int, b: int) -> int:\n    return a + b\n",
            test_code="from solution import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
            iteration=iteration,
        )

    qa_fn = lambda spec, code, max_iterations=4: run_reviewer_agent(spec, code, max_iterations=max_iterations, use_llm_critique=False)
    graph = build_squad_graph(spec_fn=_dummy_spec, coder_fn=coder_ok, reviewer_fn=qa_fn)
    result = graph.invoke({"user_request": "Build add", "iteration": 0, "max_iterations": 4, "timeline": []})
    assert calls["coder"] == 1
    assert result["iteration"] == 1
    assert result["qa_report"].status == "PASSED"
    assert result["qa_report"].tests_passed is True


def test_iteration_boundary_enforcement():
    calls = {"coder": 0}

    def coder_always_broken(spec: SpecArtifact, iteration: int, **_kw) -> CodeArtifact:
        calls["coder"] += 1
        return CodeArtifact(
            implementation_code="def add(a: int, b: int) -> int:\n    return 0\n",
            test_code="from solution import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
            iteration=iteration,
        )

    qa_fn = lambda spec, code, max_iterations=4: run_reviewer_agent(spec, code, max_iterations=max_iterations, use_llm_critique=False)
    graph = build_squad_graph(spec_fn=_dummy_spec, coder_fn=coder_always_broken, reviewer_fn=qa_fn)
    result = graph.invoke({"user_request": "Build add", "iteration": 0, "max_iterations": 4, "timeline": []})
    assert calls["coder"] == 4
    assert result["iteration"] == 4
    assert result["qa_report"].status == "MAX_CYCLES_EXCEEDED"
    assert result["qa_report"].tests_passed is False


def test_iterative_self_healing_convergence():
    def coder_self_heal(spec: SpecArtifact, iteration: int, latest_qa=None, **_kw) -> CodeArtifact:
        impl = "def add(a: int, b: int) -> int:\n    return a - b\n" if iteration == 1 else "def add(a: int, b: int) -> int:\n    return a + b\n"
        if iteration == 2:
            assert latest_qa is not None and latest_qa.tests_passed is False
        return CodeArtifact(
            implementation_code=impl,
            test_code="from solution import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
            iteration=iteration,
        )

    qa_fn = lambda spec, code, max_iterations=4: run_reviewer_agent(spec, code, max_iterations=max_iterations, use_llm_critique=False)
    graph = build_squad_graph(spec_fn=_dummy_spec, coder_fn=coder_self_heal, reviewer_fn=qa_fn)
    result = graph.invoke({"user_request": "Build add", "iteration": 0, "max_iterations": 4, "timeline": []})
    assert result["iteration"] == 2
    assert result["qa_report"].status == "PASSED"
    assert result["qa_report"].tests_passed is True
