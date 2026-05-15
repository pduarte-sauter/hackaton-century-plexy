from __future__ import annotations

import functools
import inspect
import json
import logging
import time
import traceback
from typing import Any, Callable, Optional, TypeVar

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from core.constants import *

logger = logging.getLogger("agentops.tracer")

F = TypeVar("F", bound=Callable[..., Any])

def _safe_serialize(value: Any, max_chars: int = 4000) -> str:
    try:
        serialized = json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        serialized = str(value)

    if len(serialized) > max_chars:
        serialized = serialized[:max_chars] + f"... [truncado: {len(serialized)} chars]"
    return serialized

def _capture_args(func: Callable, args: tuple, kwargs: dict) -> dict:
    try:
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        return {k: v for k, v in bound.arguments.items() if k not in ("self", "cls")}
    except Exception:
        return {"args": args, "kwargs": kwargs}

def trace_agent(name: Optional[str] = None, *, capture_input: bool = True, capture_output: bool = True):
    def decorator(func: F) -> F:
        span_name = name or f"agent.{func.__name__}"
        is_async = inspect.iscoroutinefunction(func)

        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await _run_in_span(
                    func, span_name, args, kwargs,
                    kind=trace.SpanKind.SERVER,
                    capture_input=capture_input,
                    capture_output=capture_output,
                    extra_attrs={},
                )
            return async_wrapper  # type: ignore
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return _run_in_span_sync(
                    func, span_name, args, kwargs,
                    kind=trace.SpanKind.SERVER,
                    capture_input=capture_input,
                    capture_output=capture_output,
                    extra_attrs={},
                )
            return sync_wrapper  # type: ignore
    return decorator

def trace_tool(name: Optional[str] = None, *, capture_input: bool = True, capture_output: bool = True):
    def decorator(func: F) -> F:
        span_name = name or f"tool.{func.__name__}"
        is_async = inspect.iscoroutinefunction(func)

        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await _run_in_span(
                    func, span_name, args, kwargs,
                    kind=trace.SpanKind.INTERNAL,
                    capture_input=capture_input,
                    capture_output=capture_output,
                    extra_attrs={ATTR_TOOL_NAME: span_name},
                )
            return async_wrapper  # type: ignore
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return _run_in_span_sync(
                    func, span_name, args, kwargs,
                    kind=trace.SpanKind.INTERNAL,
                    capture_input=capture_input,
                    capture_output=capture_output,
                    extra_attrs={ATTR_TOOL_NAME: span_name},
                )
            return sync_wrapper  # type: ignore
    return decorator

def trace_llm(model: Optional[str] = None, provider: Optional[str] = None, *, capture_input: bool = True, capture_output: bool = True):
    def decorator(func: F) -> F:
        span_name = f"llm.{model or func.__name__}"
        is_async = inspect.iscoroutinefunction(func)

        extra = {}
        if model:
            extra[ATTR_LLM_MODEL] = model
        if provider:
            extra[ATTR_LLM_PROVIDER] = provider

        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                result = await _run_in_span(
                    func, span_name, args, kwargs,
                    kind=trace.SpanKind.CLIENT,
                    capture_input=capture_input,
                    capture_output=capture_output,
                    extra_attrs=extra,
                    input_attr=ATTR_LLM_INPUT,
                    output_attr=ATTR_LLM_OUTPUT,
                    post_hook=_extract_token_usage,
                )
                return result
            return async_wrapper  # type: ignore
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return _run_in_span_sync(
                    func, span_name, args, kwargs,
                    kind=trace.SpanKind.CLIENT,
                    capture_input=capture_input,
                    capture_output=capture_output,
                    extra_attrs=extra,
                    input_attr=ATTR_LLM_INPUT,
                    output_attr=ATTR_LLM_OUTPUT,
                    post_hook=_extract_token_usage,
                )
            return sync_wrapper  # type: ignore
    return decorator

def _extract_token_usage(span: trace.Span, result: Any):
    try:
        usage = None
        if hasattr(result, "usage"):
            usage = result.usage
        elif isinstance(result, dict) and "usage" in result:
            usage = result["usage"]

        if usage is None:
            return

        def get(obj, *keys):
            for k in keys:
                try:
                    return obj[k] if isinstance(obj, dict) else getattr(obj, k)
                except (KeyError, AttributeError):
                    pass
            return None

        input_tokens = get(usage, "input_tokens", "prompt_tokens")
        output_tokens = get(usage, "output_tokens", "completion_tokens")

        if input_tokens is not None:
            span.set_attribute(ATTR_LLM_IN_TOKENS, int(input_tokens))
        if output_tokens is not None:
            span.set_attribute(ATTR_LLM_OUT_TOKENS, int(output_tokens))
    except Exception:
        pass

async def _run_in_span(func, span_name, args, kwargs, kind, capture_input, capture_output, extra_attrs, input_attr=None, output_attr=None, post_hook=None):
    tracer = trace.get_tracer("agentops")
    input_attr = input_attr or ATTR_AGENT_INPUT
    output_attr = output_attr or ATTR_AGENT_OUTPUT

    with tracer.start_as_current_span(span_name, kind=kind) as span:
        start = time.perf_counter()
        for k, v in extra_attrs.items():
            span.set_attribute(k, v)

        if capture_input:
            captured = _capture_args(func, args, kwargs)
            span.set_attribute(input_attr, _safe_serialize(captured))

        try:
            result = await func(*args, **kwargs)

            if capture_output:
                span.set_attribute(output_attr, _safe_serialize(result))
            if post_hook:
                post_hook(span, result)

            span.set_status(Status(StatusCode.OK))
            return result
        except Exception as exc:
            _record_exception(span, exc)
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            span.set_attribute(ATTR_DURATION_MS, round(elapsed_ms, 2))

def _run_in_span_sync(func, span_name, args, kwargs, kind, capture_input, capture_output, extra_attrs, input_attr=None, output_attr=None, post_hook=None):
    tracer = trace.get_tracer("agentops")
    input_attr = input_attr or ATTR_AGENT_INPUT
    output_attr = output_attr or ATTR_AGENT_OUTPUT

    with tracer.start_as_current_span(span_name, kind=kind) as span:
        start = time.perf_counter()
        for k, v in extra_attrs.items():
            span.set_attribute(k, v)

        if capture_input:
            captured = _capture_args(func, args, kwargs)
            span.set_attribute(input_attr, _safe_serialize(captured))

        try:
            result = func(*args, **kwargs)

            if capture_output:
                span.set_attribute(output_attr, _safe_serialize(result))
            if post_hook:
                post_hook(span, result)

            span.set_status(Status(StatusCode.OK))
            return result
        except Exception as exc:
            _record_exception(span, exc)
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            span.set_attribute(ATTR_DURATION_MS, round(elapsed_ms, 2))

def _record_exception(span: trace.Span, exc: Exception):
    span.set_status(Status(StatusCode.ERROR, str(exc)))
    span.set_attribute(ATTR_ERROR_TYPE, type(exc).__name__)
    span.set_attribute(ATTR_ERROR_MSG, str(exc))
    span.set_attribute(ATTR_ERROR_STACK, traceback.format_exc())
    span.record_exception(exc)