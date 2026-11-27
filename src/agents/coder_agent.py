from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from src.agents.spec_agent import get_gemini_llm
from src.schemas import CodeArtifact, QAReport, SpecArtifact

CODER_SYSTEM_PROMPT = (
    "You are a Senior Python Software Engineer. "
    "Given a SpecArtifact (and optionally the latest QAReport failure diff), output clean, "
    "modular Python 3.11+ implementation_code (saved as solution.py) and comprehensive pytest "
    "unit tests in test_code (saved as test_solution.py, importing from solution). "
    "Use only Python standard library modules in solution.py. Never use shell=True, eval, exec, or os.system."
)


def run_coder_agent(
    spec: SpecArtifact,
    iteration: int,
    previous_code: Optional[CodeArtifact] = None,
    latest_qa: Optional[QAReport] = None,
    inject_bug: bool = False,
    llm: Optional[BaseChatModel] = None,
) -> CodeArtifact:
    model = llm or get_gemini_llm(temperature=0.0)
    structured_llm = model.with_structured_output(CodeArtifact)
    prompt_parts = [
        f"Current Iteration: {iteration}",
        f"Technical Specification:\n{spec.model_dump_json(indent=2)}",
    ]
    if inject_bug and iteration == 1:
        prompt_parts.append(
            "ADVERSARIAL TEST MODE (Iteration 1 ONLY): Write accurate pytest unit tests matching the spec, "
            "but intentionally introduce one subtle edge-case logic bug in implementation_code so at least one test fails."
        )
    elif previous_code is not None and latest_qa is not None:
        trimmed_trace = latest_qa.execution_output[-2500:]
        prompt_parts.append(f"Previous Implementation (solution.py):\n{previous_code.implementation_code}")
        prompt_parts.append(f"Previous Tests (test_solution.py):\n{previous_code.test_code}")
        prompt_parts.append(f"QA Review Feedback: {latest_qa.review_feedback}")
        prompt_parts.append(f"Pytest Failure Output:\n{trimmed_trace}")
        prompt_parts.append("Fix the root cause identified by QA while preserving all specification invariants.")
    result = structured_llm.invoke([
        SystemMessage(content=CODER_SYSTEM_PROMPT),
        HumanMessage(content="\n\n".join(prompt_parts)),
    ])
    artifact = result if isinstance(result, CodeArtifact) else CodeArtifact.model_validate(result)
    return artifact.model_copy(update={"iteration": iteration})
