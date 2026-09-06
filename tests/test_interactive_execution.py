"""
tests/test_interactive_execution.py
Tests for interactive Docker sandbox execution with multiline stdin,
error handling, timeouts, and FastAPI execution endpoints.
"""

import pytest
from tools.sandbox import run_code_sandbox
from main import app


def test_code_execution_with_stdin():
    """TEST 4: Code execution with standard input."""
    code = (
        "a = int(input())\n"
        "b = int(input())\n"
        "print(a + b)\n"
    )
    stdin = "10\n20\n"
    result = run_code_sandbox(code=code, stdin=stdin)

    assert result["status"] == "success"
    assert result["exit_code"] == 0
    assert result["stdout"].strip() == "30"
    assert result["sandbox_used"] is True
    assert result["network_disabled"] is True


def test_invalid_code_error_handling():
    """TEST 5: Invalid Python code error captured in stderr without crashing."""
    code = (
        "def broken():\n"
        "    return 1 / 0\n"
        "broken()\n"
    )
    result = run_code_sandbox(code=code)

    assert result["status"] == "error"
    assert result["exit_code"] != 0
    assert "ZeroDivisionError" in result["stderr"]
    assert result["error"] is not None


def test_execution_timeout():
    """TEST 6: Infinite loop terminated after timeout."""
    code = "while True:\n    pass\n"
    result = run_code_sandbox(code=code, timeout=2)

    assert result["status"] == "error"
    assert "timeout" in str(result["error"]).lower()
    assert result["exit_code"] != 0


def test_multiline_stdin():
    """TEST 7: Multiline stdin values read in order."""
    code = (
        "name = input()\n"
        "age = input()\n"
        "print(name)\n"
        "print(age)\n"
    )
    stdin = "Kaustubh\n21\n"
    result = run_code_sandbox(code=code, stdin=stdin)

    assert result["status"] == "success"
    lines = result["stdout"].strip().splitlines()
    assert lines == ["Kaustubh", "21"]


import asyncio
from main import execute_code_endpoint, CodeExecuteRequest


def test_fastapi_execute_endpoint():
    """Verify execute_code_endpoint handles interactive requests with stdin."""
    req = CodeExecuteRequest(
        code="x = input()\nprint(f'Hello {x}')",
        stdin="OffAir User\n",
        language="python",
    )
    data = asyncio.run(execute_code_endpoint(req))
    assert data["status"] == "success"
    assert data["stdout"].strip() == "Hello OffAir User"
    assert data["exit_code"] == 0

