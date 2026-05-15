"""
AgentTracer SDK -- Monitoramento e Avaliacao de Agentes de IA.

Uso rapido:
    import agent_tracer_sdk as ats

    # Plug and play: captura chamadas Gemini automaticamente
    ats.init(service_name="meu-agente", auto_instrument=True)

    # Ou com decorators para funcoes customizadas
    @ats.trace(kind="agent")
    def meu_agente(pergunta):
        return responder(pergunta)
"""
from .core import init_telemetry, shutdown
from .instrumentation import trace, current_span, set_attribute
from .instrumentation.auto import enable_auto_instrumentation

__version__ = "0.1.0"


def init(
    service_name: str = None,
    export_mode: str = None,
    auto_instrument: bool = False,
):
    """
    Inicializa o AgentTracer SDK.

    Args:
        service_name: Nome do seu servico/agente.
        export_mode: "console" (dev) | "cloud" (GCP) | "otlp" (Jaeger, etc.)
        auto_instrument: Se True, captura chamadas LLM automaticamente (plug and play).
    """
    init_telemetry(service_name=service_name, export_mode=export_mode)

    if auto_instrument:
        enable_auto_instrumentation()


__all__ = [
    "init",
    "shutdown",
    "trace",
    "current_span",
    "set_attribute",
]