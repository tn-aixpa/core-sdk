from __future__ import annotations

from digitalhub.runtimes.builder import RuntimeBuilder

from digitalhub_runtime_python.runtimes.runtime import RuntimePython


class RuntimePythonBuilder(RuntimeBuilder):
    """RuntaimePythonBuilder class."""

    RUNTIME_CLASS = RuntimePython
