import time
from src.sandbox import SANDBOX_TIMEOUT_SECONDS, run_in_sandbox


def test_sandbox_passing_execution():
    impl = "def multiply(a: int, b: int) -> int:\n    return a * b\n"
    tests = "from solution import multiply\n\ndef test_mul():\n    assert multiply(3, 4) == 12\n"
    result = run_in_sandbox(impl, tests)
    assert result.exit_code == 0
    assert result.tests_passed is True
    assert result.total_tests == 1
    assert result.failed_tests == 0
    assert result.timed_out is False


def test_sandbox_failing_assertion_capture():
    impl = "def buggy() -> int:\n    return 1\n"
    tests = "from solution import buggy\n\ndef test_fail():\n    assert 1 == 2\n"
    result = run_in_sandbox(impl, tests)
    assert result.exit_code != 0
    assert result.tests_passed is False
    assert result.failed_tests >= 1
    assert "AssertionError" in result.execution_output or "assert 1 == 2" in result.execution_output


def test_sandbox_infinite_loop_timeout():
    assert SANDBOX_TIMEOUT_SECONDS == 10
    impl = "def hang() -> None:\n    while True:\n        pass\n"
    tests = "from solution import hang\n\ndef test_timeout():\n    hang()\n"
    started = time.monotonic()
    result = run_in_sandbox(impl, tests, timeout=2)
    elapsed = time.monotonic() - started
    assert elapsed < 10.0
    assert result.timed_out is True
    assert result.tests_passed is False
    assert result.exit_code != 0
    assert "TIMEOUT ERROR" in result.execution_output
