"""
tools/sandbox.py
Docker-based Python code execution sandbox.
AI-generated code NEVER runs directly on the host.
All execution happens inside an isolated container with:
- No network access
- Limited memory
- Time limit
- Ephemeral filesystem
"""

import os
import sys
import json
import subprocess
import tempfile
import textwrap
import time
from pathlib import Path
from typing import Optional

_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

from security.audit import log

import yaml
_cfg_path = os.path.join(_base, "config", "settings.yaml")
with open(_cfg_path) as f:
    _settings = yaml.safe_load(f)

_SANDBOX_CFG = _settings["sandbox"]
DOCKER_IMAGE = _SANDBOX_CFG["image"]
TIMEOUT = _SANDBOX_CFG["timeout_seconds"]
MEMORY_LIMIT = _SANDBOX_CFG["memory_limit"]
NETWORK_DISABLED = _SANDBOX_CFG["network_disabled"]


def docker_available() -> bool:
    """Check if Docker daemon is running."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _build_test_runner(code: str, tests: str) -> str:
    """
    Combine user code with test cases into a single runnable script.
    The script prints a JSON result summary.
    """
    runner = textwrap.dedent(f"""
import sys
import json
import traceback
import unittest
import io

# ─── User Code ───────────────────────────────────────────
{code}

# ─── Test Cases ──────────────────────────────────────────
{tests}

# ─── Test Runner ─────────────────────────────────────────
if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Find all test classes
    test_classes = []
    for name, obj in list(globals().items()):
        try:
            if isinstance(obj, type) and issubclass(obj, unittest.TestCase) and obj is not unittest.TestCase:
                test_classes.append(obj)
        except Exception:
            pass
    
    if not test_classes:
        # No unittest classes — run as plain script and check for errors
        try:
            exec(compile({repr(tests)}, "<tests>", "exec"), globals())
            result_data = {{"tests_total": 1, "tests_passed": 1, "tests_failed": 0, "errors": [], "output": "Script executed successfully"}}
        except Exception as e:
            result_data = {{"tests_total": 1, "tests_passed": 0, "tests_failed": 1, "errors": [str(e)], "output": traceback.format_exc()}}
    else:
        for cls in test_classes:
            suite.addTests(loader.loadTestsFromTestCase(cls))
        
        buf = io.StringIO()
        runner = unittest.TextTestRunner(stream=buf, verbosity=2)
        test_result = runner.run(suite)
        
        result_data = {{
            "tests_total": test_result.testsRun,
            "tests_passed": test_result.testsRun - len(test_result.failures) - len(test_result.errors),
            "tests_failed": len(test_result.failures) + len(test_result.errors),
            "errors": [str(e) for _, e in test_result.failures + test_result.errors],
            "output": buf.getvalue(),
        }}
    
    print("===RESULT_JSON===")
    print(json.dumps(result_data))
""")
    return runner


def run_python_sandbox(
    code: str,
    tests: str = "",
    timeout: int = TIMEOUT,
) -> dict:
    """
    Execute Python code inside a Docker sandbox.

    Args:
        code: The generated Python code to run.
        tests: Test cases (unittest or plain assertions).
        timeout: Maximum execution time in seconds.

    Returns:
        {
            "success": bool,
            "stdout": str,
            "stderr": str,
            "tests_passed": int,
            "tests_total": int,
            "tests_failed": int,
            "sandbox_used": True,
            "network_disabled": True,
            "error": str | None,
        }
    """
    if not docker_available():
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "tests_passed": 0,
            "tests_total": 0,
            "tests_failed": 0,
            "sandbox_used": False,
            "network_disabled": False,
            "error": "Docker is not available. Start Docker Desktop first.",
        }

    log("SANDBOX_START", network_disabled=NETWORK_DISABLED, timeout=timeout)

    # Build the runner script
    runner_code = _build_test_runner(code, tests)

    # Write to a temporary file
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
        prefix="sih_sandbox_",
    ) as f:
        f.write(runner_code)
        script_path = f.name

    try:
        # Build docker run command
        docker_cmd = [
            "docker", "run",
            "--rm",                          # Remove container after exit
            "--memory", MEMORY_LIMIT,        # Memory limit
            "--memory-swap", MEMORY_LIMIT,   # No swap
            "--cpus", "1.0",                 # CPU limit
            "-v", f"{script_path}:/sandbox/run.py:ro",  # Mount script read-only
            "--workdir", "/sandbox",
        ]

        if NETWORK_DISABLED:
            docker_cmd.extend(["--network", "none"])

        docker_cmd.extend([DOCKER_IMAGE, "python", "/sandbox/run.py"])

        t0 = time.time()
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 5,  # Extra buffer for container startup
        )
        elapsed = round(time.time() - t0, 2)

        stdout = result.stdout
        stderr = result.stderr

        # Parse JSON result from stdout
        test_data = {
            "tests_total": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": [],
            "output": stdout,
        }

        if "===RESULT_JSON===" in stdout:
            try:
                json_part = stdout.split("===RESULT_JSON===")[-1].strip()
                test_data = json.loads(json_part)
                # Clean output (remove JSON part)
                stdout = stdout.split("===RESULT_JSON===")[0].strip()
            except json.JSONDecodeError:
                pass

        success = result.returncode == 0 and test_data.get("tests_failed", 0) == 0

        log(
            "SANDBOX_EXECUTION",
            success=success,
            elapsed_s=elapsed,
            network_disabled=NETWORK_DISABLED,
            tests_passed=test_data.get("tests_passed", 0),
            tests_total=test_data.get("tests_total", 0),
            sandbox_used=True,
        )

        return {
            "success": success,
            "stdout": stdout[:5000],
            "stderr": stderr[:2000],
            "tests_passed": test_data.get("tests_passed", 0),
            "tests_total": test_data.get("tests_total", 0),
            "tests_failed": test_data.get("tests_failed", 0),
            "test_output": test_data.get("output", ""),
            "errors": test_data.get("errors", []),
            "sandbox_used": True,
            "network_disabled": NETWORK_DISABLED,
            "elapsed_s": elapsed,
            "error": None if success else (stderr[:500] or "Tests failed"),
        }

    except subprocess.TimeoutExpired:
        log("SANDBOX_TIMEOUT", timeout=timeout)
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Execution timed out after {timeout}s",
            "tests_passed": 0,
            "tests_total": 0,
            "tests_failed": 0,
            "sandbox_used": True,
            "network_disabled": NETWORK_DISABLED,
            "error": f"Sandbox timeout ({timeout}s)",
        }
    except Exception as e:
        log("SANDBOX_ERROR", error=str(e))
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "tests_passed": 0,
            "tests_total": 0,
            "tests_failed": 0,
            "sandbox_used": True,
            "network_disabled": NETWORK_DISABLED,
            "error": str(e),
        }
    finally:
        # Clean up temp file
        try:
            Path(script_path).unlink(missing_ok=True)
        except Exception:
            pass


def run_code_sandbox(
    code: str,
    language: str = "python",
    stdin: str = "",
    timeout: int = TIMEOUT,
) -> dict:
    """
    Execute arbitrary untrusted code in an ephemeral, isolated Docker container with stdin support.

    Args:
        code: Code string to execute.
        language: Programming language (default: python).
        stdin: Standard input to pipe into the program (supports multiline strings).
        timeout: Maximum execution duration in seconds.

    Returns:
        {
            "status": "success" | "error",
            "stdout": str,
            "stderr": str,
            "exit_code": int,
            "execution_time": float,
            "sandbox_used": bool,
            "network_disabled": bool,
            "error": Optional[str],
        }
    """
    if language.lower() not in ("python", "py", "python3"):
        return {
            "status": "error",
            "stdout": "",
            "stderr": f"Unsupported language '{language}'. Only Python is supported in this sandbox.",
            "exit_code": 1,
            "execution_time": 0.0,
            "sandbox_used": False,
            "network_disabled": False,
            "error": f"Unsupported language '{language}'",
        }

    if not docker_available():
        return {
            "status": "error",
            "stdout": "",
            "stderr": "Docker daemon is not available. Please start Docker Desktop.",
            "exit_code": -1,
            "execution_time": 0.0,
            "sandbox_used": False,
            "network_disabled": False,
            "error": "Docker is not available",
        }

    log("SANDBOX_START", mode="interactive", network_disabled=NETWORK_DISABLED, timeout=timeout)

    import uuid
    container_name = f"sih_interactive_{uuid.uuid4().hex[:8]}"

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
        prefix="sih_interactive_",
        encoding="utf-8",
    ) as f:
        f.write(code)
        script_path = f.name

    try:
        docker_cmd = [
            "docker", "run",
            "-i",                            # Keep STDIN open
            "--name", container_name,        # Unique name for explicit cleanup on timeout
            "--rm",                          # Ephemeral
            "--memory", MEMORY_LIMIT,        # Memory restriction (e.g. 256m)
            "--memory-swap", MEMORY_LIMIT,   # Disable swap expansion
            "--cpus", "1.0",                 # CPU restriction
            "-v", f"{script_path}:/sandbox/app.py:ro",  # Read-only mount
            "--workdir", "/sandbox",
        ]

        if NETWORK_DISABLED:
            docker_cmd.extend(["--network", "none"])

        docker_cmd.extend([DOCKER_IMAGE, "python", "-u", "/sandbox/app.py"])

        t0 = time.time()
        result = subprocess.run(
            docker_cmd,
            input=stdin if stdin is not None else "",
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = round(time.time() - t0, 3)

        success = (result.returncode == 0)
        stdout = result.stdout
        stderr = result.stderr

        log(
            "SANDBOX_EXECUTION",
            mode="interactive",
            success=success,
            elapsed_s=elapsed,
            exit_code=result.returncode,
            network_disabled=NETWORK_DISABLED,
            sandbox_used=True,
        )

        return {
            "status": "success" if success else "error",
            "stdout": stdout[:10000],
            "stderr": stderr[:5000],
            "exit_code": result.returncode,
            "execution_time": elapsed,
            "sandbox_used": True,
            "network_disabled": NETWORK_DISABLED,
            "error": None if success else (stderr.strip() or f"Process exited with code {result.returncode}"),
        }

    except subprocess.TimeoutExpired:
        # Force remove container if still running
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
        log("SANDBOX_TIMEOUT", mode="interactive", timeout=timeout)
        return {
            "status": "error",
            "stdout": "",
            "stderr": f"Execution timed out after {timeout} seconds.",
            "exit_code": 124,
            "execution_time": float(timeout),
            "sandbox_used": True,
            "network_disabled": NETWORK_DISABLED,
            "error": f"Sandbox timeout ({timeout}s)",
        }

    except Exception as e:
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
        log("SANDBOX_ERROR", mode="interactive", error=str(e))
        return {
            "status": "error",
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "execution_time": 0.0,
            "sandbox_used": True,
            "network_disabled": NETWORK_DISABLED,
            "error": str(e),
        }

    finally:
        try:
            Path(script_path).unlink(missing_ok=True)
        except Exception:
            pass

