"""
Decorator @trace - instrumenta qualquer funcao com OpenTelemetry.
Suporta sync e async. Um decorator para agent, tool e llm.
"""
import functools
import inspect
import json
import time
import logging
from datetime import datetime, timezone
from typing import Any

from opentelemetry import trace as otel_trace, metrics
from opentelemetry.trace import StatusCode

logger = logging.getLogger("agent_tracer")

_SPAN_KINDS = {
    "agent": otel_trace.SpanKind.SERVER,
    "tool": otel_trace.SpanKind.INTERNAL,
    "llm": otel_trace.SpanKind.CLIENT,
}

_meter = None
_counters = {}
_histograms = {}


def _get_meter():
    global _meter
    if _meter is None:
        _meter = metrics.get_meter("agent_tracer")
    return _meter


def _counter(name: str, description: str = ""):
    if name not in _counters:
        _counters[name] = _get_meter().create_counter(name, description=description)
    return _counters[name]


def _histogram(name: str, description: str = "", unit: str = "ms"):
    if name not in _histograms:
        _histograms[name] = _get_meter().create_histogram(name, description=description, unit=unit)
    return _histograms[name]


def trace(kind: str = "agent", model: str = None, provider: str = None, capture_io: bool = True):
    """
    Decorator universal de tracing.
    """
    span_kind = _SPAN_KINDS.get(kind, otel_trace.SpanKind.INTERNAL)

    def decorator(func):
        func_name = func.__name__
        span_name = f"{kind}.{func_name}"
        is_async = inspect.iscoroutinefunction(func)

        def _record_span(span, func, args, kwargs, result=None, error=None, elapsed_ms=0):
            """Registra todos os atributos no span de forma padronizada."""

            span.set_attribute("agent_tracer.kind", kind)
            span.set_attribute("agent_tracer.timestamp", datetime.now(timezone.utc).isoformat())
            span.set_attribute("agent_tracer.latency_ms", round(elapsed_ms, 2))
            span.set_attribute("agent_tracer.status", "error" if error else "success")

            input_str = _serialize_args(func, args, kwargs) if capture_io else ""

            if kind == "agent":
                span.set_attribute("agent_tracer.agent_name", func_name)
                span.set_attribute("agent_tracer.prompt", input_str)
                if result is not None:
                    span.set_attribute("agent_tracer.completion", _safe_str(result))

            elif kind == "tool":
                span.set_attribute("agent_tracer.tool_name", func_name)
                span.set_attribute("agent_tracer.tool_input", input_str)
                if result is not None:
                    span.set_attribute("agent_tracer.tool_output", _safe_str(result))

            elif kind == "llm":
                span.set_attribute("agent_tracer.prompt", input_str)
                if result is not None:
                    span.set_attribute("agent_tracer.completion", _extract_text(result))
                if model:
                    span.set_attribute("agent_tracer.model", model)
                if provider:
                    span.set_attribute("agent_tracer.provider", provider)

                # Token usage
                tokens = _extract_tokens(result)
                if tokens:
                    span.set_attribute("agent_tracer.input_tokens", tokens["input"])
                    span.set_attribute("agent_tracer.output_tokens", tokens["output"])
                    span.set_attribute("agent_tracer.total_tokens", tokens["total"])

            if error:
                span.set_attribute("agent_tracer.error_type", type(error).__name__)
                span.set_attribute("agent_tracer.error_message", str(error))
                span.record_exception(error)
                span.set_status(otel_trace.Status(StatusCode.ERROR, str(error)))
            else:
                span.set_status(otel_trace.Status(StatusCode.OK))

        def _record_metrics(span_name, kind, elapsed_ms, error=None, tokens=None):
            labels = {"name": span_name, "kind": kind}
            _counter("agent_tracer.calls", "Total de chamadas").add(1, labels)
            _histogram("agent_tracer.latency", "Latencia").record(elapsed_ms, labels)
            if error:
                _counter("agent_tracer.errors", "Total de erros").add(1, labels)
            if tokens:
                _counter("agent_tracer.tokens", "Total de tokens").add(tokens["total"], labels)

        def _execute(func, args, kwargs):
            tracer = otel_trace.get_tracer("agent_tracer")
            with tracer.start_as_current_span(span_name, kind=span_kind) as span:
                start = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    elapsed = (time.perf_counter() - start) * 1000
                    tokens = _extract_tokens(result) if kind == "llm" else None
                    _record_span(span, func, args, kwargs, result=result, elapsed_ms=elapsed)
                    _record_metrics(span_name, kind, elapsed, tokens=tokens)
                    return result
                except Exception as exc:
                    elapsed = (time.perf_counter() - start) * 1000
                    _record_span(span, func, args, kwargs, error=exc, elapsed_ms=elapsed)
                    _record_metrics(span_name, kind, elapsed, error=exc)
                    raise

        async def _execute_async(func, args, kwargs):
            tracer = otel_trace.get_tracer("agent_tracer")
            with tracer.start_as_current_span(span_name, kind=span_kind) as span:
                start = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    elapsed = (time.perf_counter() - start) * 1000
                    tokens = _extract_tokens(result) if kind == "llm" else None
                    _record_span(span, func, args, kwargs, result=result, elapsed_ms=elapsed)
                    _record_metrics(span_name, kind, elapsed, tokens=tokens)
                    return result
                except Exception as exc:
                    elapsed = (time.perf_counter() - start) * 1000
                    _record_span(span, func, args, kwargs, error=exc, elapsed_ms=elapsed)
                    _record_metrics(span_name, kind, elapsed, error=exc)
                    raise

        if is_async:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                return await _execute_async(func, args, kwargs)
            return wrapper
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return _execute(func, args, kwargs)
            return wrapper

    return decorator


# --- Helpers ---

def _safe_str(value: Any, max_len: int = 4000) -> str:
    """Serializa valor para string, truncando se necessario."""
    try:
        s = json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        s = str(value)
    return s[:max_len] if len(s) > max_len else s


def _serialize_args(func, args, kwargs) -> str:
    """Captura argumentos da funcao como JSON."""
    try:
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        cleaned = {k: v for k, v in bound.arguments.items() if k not in ("self", "cls")}
        return _safe_str(cleaned)
    except Exception:
        return _safe_str({"args": str(args), "kwargs": str(kwargs)})


def _extract_text(result) -> str:
    """Extrai texto da resposta LLM (suporta Google GenAI, OpenAI, dict)."""
    # Google GenAI: response.text
    if hasattr(result, "text"):
        return _safe_str(result.text)
    # Dict com campo text
    if isinstance(result, dict):
        return _safe_str(result.get("text", result.get("content", result)))
    return _safe_str(result)


def _extract_tokens(result) -> dict | None:
    """Extrai token usage de respostas LLM. Retorna dict ou None."""
    if result is None:
        return None
    try:
        usage = getattr(result, "usage_metadata", None) or getattr(result, "usage", None)
        if not usage and isinstance(result, dict):
            usage = result.get("usage")
        if not usage:
            return None

        input_t = 0
        output_t = 0
        for key in ["input_tokens", "prompt_tokens", "prompt_token_count"]:
            val = getattr(usage, key, None) if not isinstance(usage, dict) else usage.get(key)
            if val is not None:
                input_t = int(val)
                break
        for key in ["output_tokens", "completion_tokens", "candidates_token_count"]:
            val = getattr(usage, key, None) if not isinstance(usage, dict) else usage.get(key)
            if val is not None:
                output_t = int(val)
                break

        if input_t or output_t:
            return {"input": input_t, "output": output_t, "total": input_t + output_t}
    except Exception:
        pass
    return None


# --- Context helpers ---

def current_span():
    """Retorna o span atual em execucao."""
    return otel_trace.get_current_span()


def set_attribute(key: str, value: Any):
    """Adiciona atributo customizado ao span atual."""
    span = otel_trace.get_current_span()
    if span and span.is_recording():
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False, default=str)
        span.set_attribute(key, value)