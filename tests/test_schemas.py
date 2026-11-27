import pytest
from pydantic import ValidationError
from src.schemas import CodeArtifact, QAReport, SpecArtifact


def test_schema_serialization_and_validation():
    spec = SpecArtifact(
        feature_name="TokenBucket",
        requirements=["Thread-safe mutex lock", "Microsecond precision"],
        test_cases=["test_burst_exhaustion", "test_refill_rate"],
        interfaces="class TokenBucket: ...",
    )
    restored_spec = SpecArtifact.model_validate_json(spec.model_dump_json())
    assert restored_spec == spec

    code = CodeArtifact(implementation_code="x = 1", test_code="def test_x(): assert True", iteration=1)
    assert CodeArtifact.model_validate_json(code.model_dump_json()).iteration == 1

    report = QAReport(
        tests_passed=True,
        total_tests=2,
        failed_tests=0,
        execution_output="2 passed",
        review_feedback=["LGTM"],
        status="PASSED",
    )
    assert QAReport.model_validate_json(report.model_dump_json()).status == "PASSED"

    with pytest.raises(ValidationError):
        SpecArtifact(feature_name="", requirements=[], test_cases=["t1"], interfaces="pass")
    with pytest.raises(ValidationError):
        CodeArtifact(implementation_code="x = 1", test_code="pass", iteration=0)
    with pytest.raises(ValidationError):
        QAReport(tests_passed=False, total_tests=1, failed_tests=1, execution_output="err", status="INVALID")
