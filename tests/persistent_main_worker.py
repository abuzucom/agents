#!/usr/bin/env python3
"""Run a Python CLI entrypoint repeatedly with isolated request state."""
import atexit
import json
import subprocess
import sys
from pathlib import Path


_WORKER_CODE = r"""
import contextlib
import importlib.util
import io
import json
import os
import sys

module_path = sys.argv[1]
spec = importlib.util.spec_from_file_location("persistent_main", module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
main = getattr(module, "main")
request_stream = sys.stdin
response_stream = sys.stdout
for line in request_stream:
    request = json.loads(line)
    output = io.StringIO()
    error = io.StringIO()
    old_argv = sys.argv
    old_cwd = os.getcwd()
    old_environment = os.environ.copy()
    old_stdin = sys.stdin
    try:
        os.chdir(request["cwd"])
        os.environ.clear()
        os.environ.update(request["environment"])
        sys.argv = [module_path, *request["arguments"]]
        sys.stdin = io.StringIO(request["stdin"])
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            code = main()
        response = {
            "code": code,
            "stdout": output.getvalue(),
            "stderr": error.getvalue(),
        }
    except Exception as worker_error:
        response = {
            "worker_error": f"{type(worker_error).__name__}: {worker_error}",
        }
    finally:
        sys.argv = old_argv
        os.chdir(old_cwd)
        os.environ.clear()
        os.environ.update(old_environment)
        sys.stdin = old_stdin
    response_stream.write(json.dumps(response) + "\n")
    response_stream.flush()
"""


class MainWorker:
    """Keep one imported CLI module alive across isolated invocations."""

    def __init__(self, module_path: Path):
        self.module_path = Path(module_path)
        self.process = subprocess.Popen(
            [sys.executable, "-c", _WORKER_CODE, str(self.module_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        atexit.register(self.close)

    def invoke(self, arguments: list[str], payload, cwd: Path,
               environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
        """Run one isolated request and return a completed-process result."""
        if self.process.stdin is None or self.process.stdout is None:
            raise RuntimeError("persistent main worker pipes are unavailable")
        request = {
            "arguments": list(arguments),
            "cwd": str(cwd),
            "environment": dict(environment),
            "stdin": "" if payload is None else json.dumps(payload),
        }
        self.process.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        response_line = self.process.stdout.readline()
        if not response_line:
            code = self.process.poll()
            raise RuntimeError(f"persistent main worker exited without output: {code}")
        response = json.loads(response_line)
        if "worker_error" in response:
            raise RuntimeError(response["worker_error"])
        command = [sys.executable, str(self.module_path), *arguments]
        return subprocess.CompletedProcess(
            command, response["code"], response["stdout"], response["stderr"])

    def close(self) -> None:
        """Close the request stream and join the worker process."""
        if self.process.poll() is not None:
            return
        if self.process.stdin is not None and not self.process.stdin.closed:
            self.process.stdin.close()
        self.process.wait()
