from typing import Any
from opentelemetry import trace
import json

def current_span() -> trace.Span:

    return trace.get_current_span()

def set_attribute(key: str, value: Any) -> None:
    """
    Adiciona um atributo customizado ao span que está sendo executado agora.
    Excelente para registrar IDs de usuários, métricas de negócio ou estados internos.

    Args:
        key: O nome do atributo (ex: "user.id", "business.status")
        value: O valor. Se for dict/list, será serializado para JSON.
    """
    span = trace.get_current_span()
    
    if span and span.is_recording():
        if isinstance(value, (dict, list)):
            try:
                value = json.dumps(value, ensure_ascii=False)
            except Exception:
                value = str(value)
        
        span.set_attribute(key, value)