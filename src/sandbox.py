import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from pydantic import BaseModel

SANDBOX_TIMEOUT_SECONDS: int = 10


class SandboxResult(BaseModel):
    exit_code: int
    tests_passed: bool
    total_tests: int
    failed_tests: int
    execution_output: str
    timed_out: bool = False


def _parse_pytest_counts(output: str, exit_code: int) -> tuple[int, int]:
    passed = sum(int(m) for m in re.findall(r"(\d+)\s+passed", output))
    failed = sum(int(m) for m in re.findall(r"(\d+)\s+(?:failed|error|errors)", output))
    total = passed + failed
    if total == 0 and exit_code != 0:
        return 1, 1
    return total, failed


def run_in_sandbox(
    implementation_code: str,
    test_code: str,
    timeout: int = SANDBOX_TIMEOUT_SECONDS,
) -> SandboxResult:
    safe_env = {k: v for k, v in os.environ.items() if "KEY" not in k and "SECRET" not in k and "TOKEN" not in k}
    safe_env["PYTHONDONTWRITEBYTECODE"] = "1"
    with tempfile.TemporaryDirectory(prefix="squad_sandbox_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        (tmp_path / "solution.py").write_text(implementation_code, encoding="utf-8")
        (tmp_path / "test_solution.py").write_text(test_code, encoding="utf-8")
        cmd = [sys.executable, "-m", "pytest", "test_solution.py", "-v", "--tb=short"]
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(tmp_path),
                env=safe_env,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            combined = (proc.stdout + "\n" + proc.stderr).strip()
            total, failed = _parse_pytest_counts(combined, proc.returncode)
            passed = proc.returncode == 0 and total > 0 and failed == 0
            return SandboxResult(
                exit_code=proc.returncode,
                tests_passed=passed,
                total_tests=total,
                failed_tests=failed,
                execution_output=combined,
                timed_out=False,
            )
        except subprocess.TimeoutExpired as exc:
            partial = ((exc.stdout or "") + "\n" + (exc.stderr or "")).strip()
            msg = f"TIMEOUT ERROR: Sandbox killed process after {timeout}s limit.\n{partial}".strip()
            return SandboxResult(
                exit_code=-1,
                tests_passed=False,
                total_tests=1,
                failed_tests=1,
                execution_output=msg,
                timed_out=True,
            )
