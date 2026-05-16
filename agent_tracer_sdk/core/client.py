"""
Core do AgentTracer — inicializa OpenTelemetry (traces + métricas).
"""
import logging
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,
    ConsoleMetricExporter,
)

from .. import config

logger = logging.getLogger("agent_tracer")

_initialized = False


def init_telemetry(
    service_name: str = None,
    export_mode: str = None,
):
    global _initialized
    if _initialized:
        logger.warning("AgentTracer já inicializado — ignorando chamada duplicada.")
        return

    service_name = service_name or config.SERVICE_NAME
    export_mode = export_mode or config.EXPORT_MODE

    resource = Resource.create({
        "service.name": service_name,
        "service.version": config.SERVICE_VERSION,
    })

    # traces
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(_create_span_exporter(export_mode))
    )
    if export_mode == "cloud":
        from .exporters import GCPLoggingExporter
        tracer_provider.add_span_processor(
            BatchSpanProcessor(GCPLoggingExporter(project_id=config.GCP_PROJECT))
        )
    
    # Adiciona o exporter do MLflow se a URL estiver configurada
    if config.MLFLOW_API_URL:
        from .exporters import MLFlowAPIExporter
        tracer_provider.add_span_processor(
            BatchSpanProcessor(MLFlowAPIExporter(api_url=config.MLFLOW_API_URL))
        )

    trace.set_tracer_provider(tracer_provider)

    # métricas
    metric_reader = PeriodicExportingMetricReader(
        _create_metric_exporter(export_mode),
        export_interval_millis=15000,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    _initialized = True
    logger.info("AgentTracer iniciado | service=%s | mode=%s", service_name, export_mode)


def shutdown():
    provider = trace.get_tracer_provider()
    if hasattr(provider, "shutdown"):
        provider.shutdown()

    meter = metrics.get_meter_provider()
    if hasattr(meter, "shutdown"):
        meter.shutdown()

    logger.info("AgentTracer encerrado.")


def _create_span_exporter(mode: str):
    """Cria o exporter de spans baseado no modo."""
    if mode == "cloud":
        # Desabilitado para evitar erro 403 de IAM no Cloud Trace
        # Mantendo apenas o GCPLoggingExporter (BigQuery) e MLFlow
        import os
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter
        return ConsoleSpanExporter(out=open(os.devnull, "w"))

    if mode == "otlp":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        return OTLPSpanExporter(endpoint=f"{config.OTLP_ENDPOINT}/v1/traces")

    from .exporters import CleanConsoleExporter
    return CleanConsoleExporter()


def _create_metric_exporter(mode: str):
    """Cria o exporter de métricas baseado no modo."""
    if mode == "cloud":
        # Desabilitado para evitar erro 403 de IAM no Cloud Run
        # Já que a análise será feita no MLflow e BigQuery.
        import os
        return ConsoleMetricExporter(out=open(os.devnull, "w"))

    if mode == "otlp":
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        return OTLPMetricExporter(endpoint=f"{config.OTLP_ENDPOINT}/v1/metrics")

    import os
    return ConsoleMetricExporter(out=open(os.devnull, "w"))