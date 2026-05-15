"""
Auto-instrumentacao — intercepta chamadas ao Google GenAI (Gemini)
automaticamente, sem precisar decorar funcoes.
"""
import logging
import os

logger = logging.getLogger("agent_tracer")


def enable_auto_instrumentation():
    """
    Ativa auto-instrumentacao para bibliotecas de LLM suportadas.
    Atualmente suporta: Google GenAI (Gemini).
    """
    _instrument_google_genai()


def _instrument_google_genai():
    """Instrumenta o Google GenAI SDK (Gemini)."""
    try:
        from opentelemetry.instrumentation.google_genai import GoogleGenAiSdkInstrumentor

        # Habilita captura de conteudo (prompts e respostas)
        os.environ.setdefault(
            "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "true"
        )

        GoogleGenAiSdkInstrumentor().instrument()
        logger.info("Auto-instrumentacao ativada: Google GenAI (Gemini)")

    except ImportError:
        logger.warning(
            "opentelemetry-instrumentation-google-genai nao instalado. "
            "Instale com: pip install opentelemetry-instrumentation-google-genai"
        )
    except Exception as e:
        logger.warning("Falha ao instrumentar Google GenAI: %s", e)
