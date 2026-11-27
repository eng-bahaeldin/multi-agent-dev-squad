from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from src.agents.spec_agent import get_gemini_llm
from src.sandbox import SandboxResult, run_in_sandbox
from src.schemas import CodeArtifact, QAReport, SpecArtifact

FORBIDDEN_PATTERNS: tuple[str, ...] = (
    "os.system(",
    "subprocess.",
    "eval(",
    "exec(",
    "__import__(",
    "shell=True",
)


class _CritiqueList(BaseModel):
    items: list[str] = Field(default_factory=list)


def _audit_security(source_code: str) -> list[str]:
    findings = []
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in source_code:
            findings.append(f"SECURITY VIOLATION: Forbidden primitive detected ({pattern}).")
    return findings


def _generate_llm_critique(spec: SpecArtifact, code: CodeArtifact, trace: str, llm: Optional[BaseChatModel]) -> list[str]:
    try:
        model = llm or get_gemini_llm(temperature=0.0)
        critic = model.with_structured_output(_CritiqueList)
        res = critic.invoke([
            SystemMessage(content="You are a QA Code Auditor. Summarize concise, actionable root-cause fixes from the pytest failure trace."),
            HumanMessage(content=f"Spec: {spec.feature_name}\nCode:\n{code.implementation_code}\n\nTrace:\n{trace[-2000:]}"),
        ])
        parsed = res if isinstance(res, _CritiqueList) else _CritiqueList.model_validate(res)
        return parsed.items[:5]
    except Exception:
        return []


def run_reviewer_agent(
    spec: SpecArtifact,
    code: CodeArtifact,
    max_iterations: int = 4,
    llm: Optional[BaseChatModel] = None,
    use_llm_critique: bool = True,
) -> QAReport:
    security_issues = _audit_security(code.implementation_code)
    sandbox_res: SandboxResult = run_in_sandbox(code.implementation_code, code.test_code)
    all_passed = bool(sandbox_res.tests_passed and len(security_issues) == 0)
    feedback: list[str] = list(security_issues)
    if all_passed:
        feedback.append("LGTM: All sandboxed pytest assertions passed with zero security findings.")
        status = "PASSED"
    else:
        if sandbox_res.timed_out:
            feedback.append("TIMEOUT: Execution exceeded 10s sandbox limit; check for infinite loops or deadlocks.")
        if use_llm_critique:
            feedback.extend(_generate_llm_critique(spec, code, sandbox_res.execution_output, llm))
        if not feedback:
            feedback.append(f"Pytest exited with code {sandbox_res.exit_code}. Inspect execution_output trace.")
        status = "MAX_CYCLES_EXCEEDED" if code.iteration >= max_iterations else "NEEDS_REVISION"
    return QAReport(
        tests_passed=all_passed,
        total_tests=sandbox_res.total_tests,
        failed_tests=0 if all_passed else max(1, sandbox_res.failed_tests),
        execution_output=sandbox_res.execution_output,
        review_feedback=feedback,
        status=status,
    )
