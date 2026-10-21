"""Safe, isolated code execution sandbox for coding assessments.

CRITICAL SECURITY CONSTRAINTS:
- Executes code ONLY in an isolated subprocess with strict timeouts.
- Never executes code directly in the main FastAPI server process or event loop.
- Strips all sensitive environment variables (API keys, DB credentials).
- Restricts dangerous AST operations and system calls (sockets, forks, file deletes).
- Runs within a temporary disposable directory.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_TIMEOUT_SECONDS = 3.5
MAX_OUTPUT_LENGTH = 8192

# Disallowed modules and builtins to prevent system compromise
BANNED_MODULES = {
    "socket",
    "subprocess",
    "pty",
    "shutil",
    "ctypes",
    "winreg",
    "msvcrt",
    "_winapi",
    "multiprocessing",
    "threading",
    "webbrowser",
    "antigravity",
    "http",
    "urllib",
    "requests",
    "httpx",
}

BANNED_CALLS = {
    "system",
    "spawn",
    "popen",
    "execv",
    "execve",
    "fork",
    "kill",
    "remove",
    "unlink",
    "rmdir",
}


class SecurityViolationError(Exception):
    """Raised when submitted code contains prohibited modules or dangerous calls."""
    pass


def scan_code_security(code_str: str) -> Optional[str]:
    """Parse code with AST to detect dangerous imports or function calls.

    Returns:
        None if safe, or an error message string if a security violation is found.
    """
    try:
        tree = ast.parse(code_str)
    except SyntaxError as e:
        return f"Syntax Error: {e.msg} at line {e.lineno}"

    for node in ast.walk(tree):
        # 1. Check direct imports: `import socket`
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_module = alias.name.split(".")[0]
                if root_module in BANNED_MODULES:
                    return f"Security Violation: Import of restricted module '{alias.name}' is prohibited."

        # 2. Check from imports: `from subprocess import run`
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_module = node.module.split(".")[0]
                if root_module in BANNED_MODULES:
                    return f"Security Violation: Import from restricted module '{node.module}' is prohibited."

        # 3. Check dangerous function calls: `os.system('...')`
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in BANNED_CALLS:
                    return f"Security Violation: Calling restricted function '{node.func.attr}' is prohibited."
            elif isinstance(node.func, ast.Name):
                if node.func.id in ("eval", "exec", "__import__"):
                    return f"Security Violation: Built-in '{node.func.id}' execution is restricted in assessments."

    return None


def execute_python_code(
    code_str: str,
    stdin_input: str = "",
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """Execute Python code in an isolated child process with timeout and sanitized env.

    Returns dict with:
        success: bool
        stdout: str
        stderr: str
        execution_time_ms: float
        error: Optional[str]
    """
    # 1. AST Security Analysis
    security_error = scan_code_security(code_str)
    if security_error:
        return {
            "success": False,
            "stdout": "",
            "stderr": security_error,
            "execution_time_ms": 0.0,
            "error": security_error,
        }

    # 2. Sanitize environment (strip tokens, keys, DB URLs)
    clean_env = {
        "PYTHONIOENCODING": "utf-8",
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
    }

    start_time = time.perf_counter()

    # 3. Run in temporary isolated directory
    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = os.path.join(temp_dir, "solution.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code_str)

        try:
            # Use current venv python executable
            python_bin = sys.executable

            process = subprocess.run(
                [python_bin, "-u", script_path],
                input=stdin_input,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=temp_dir,
                env=clean_env,
            )

            execution_time = round((time.perf_counter() - start_time) * 1000, 2)
            stdout = process.stdout[:MAX_OUTPUT_LENGTH]
            stderr = process.stderr[:MAX_OUTPUT_LENGTH]

            if process.returncode == 0:
                return {
                    "success": True,
                    "stdout": stdout,
                    "stderr": stderr,
                    "execution_time_ms": execution_time,
                    "error": None,
                }
            else:
                return {
                    "success": False,
                    "stdout": stdout,
                    "stderr": stderr,
                    "execution_time_ms": execution_time,
                    "error": stderr or f"Process exited with non-zero code {process.returncode}",
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout_seconds} seconds.",
                "execution_time_ms": round(timeout_seconds * 1000, 2),
                "error": "Time Limit Exceeded",
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "execution_time_ms": 0.0,
                "error": f"Execution failed: {str(e)}",
            }


def evaluate_test_cases(
    user_code: str,
    test_cases: List[Dict[str, Any]],
    function_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Run code against multiple test cases and compute accuracy.

    Test cases can be:
    - input/output via stdin and stdout
    - function invocation test runner: f"{user_code}\nprint({function_name}({tc['input']}))"
    """
    if not test_cases:
        # Single execution test
        result = execute_python_code(user_code)
        return {
            "all_passed": result["success"],
            "passed_count": 1 if result["success"] else 0,
            "total_count": 1,
            "results": [result],
        }

    results: List[Dict[str, Any]] = []
    passed_count = 0

    for i, tc in enumerate(test_cases, 1):
        raw_input = str(tc.get("input", ""))
        expected_output = str(tc.get("expected_output", "")).strip()
        is_hidden = bool(tc.get("is_hidden", False))

        # Check if function call wrapper or stdin execution
        if function_name and f"def {function_name}" in user_code:
            runner_script = (
                f"{user_code}\n\n"
                f"if __name__ == '__main__':\n"
                f"    print({function_name}({raw_input}))\n"
            )
            exec_res = execute_python_code(runner_script)
        else:
            exec_res = execute_python_code(user_code, stdin_input=raw_input)

        actual_output = exec_res["stdout"].strip()
        passed = (exec_res["success"] and actual_output == expected_output)

        if passed:
            passed_count += 1

        results.append({
            "test_case_index": i,
            "is_hidden": is_hidden,
            "passed": passed,
            "input": "<Hidden>" if is_hidden else raw_input,
            "expected_output": "<Hidden>" if is_hidden else expected_output,
            "actual_output": "<Hidden>" if is_hidden and not passed else actual_output,
            "execution_time_ms": exec_res["execution_time_ms"],
            "error": exec_res["error"],
        })

    all_passed = (passed_count == len(test_cases))
    return {
        "all_passed": all_passed,
        "passed_count": passed_count,
        "total_count": len(test_cases),
        "score_percentage": round((passed_count / len(test_cases)) * 100, 1) if test_cases else 0.0,
        "results": results,
    }
