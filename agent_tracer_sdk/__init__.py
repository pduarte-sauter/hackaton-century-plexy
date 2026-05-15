from .core.client import init, get_client
from .instrumentation.decorators import trace_agent, trace_tool, trace_llm

__all__ = [
    "init",
    "get_client",
    "trace_agent",
    "trace_tool",
    "trace_llm",
    "current_span",  # A implementar em context.py
    "set_attribute", # A implementar em context.py
]

__version__ = "0.1.0"