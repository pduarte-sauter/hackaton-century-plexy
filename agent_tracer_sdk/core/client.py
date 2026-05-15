import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from config import get_api_key, get_endpoint

logger = logging.getLogger("agentops")

_client: Optional["AgentOpsClient"] = None

class AgentOpsClient:
    def __init__(
        self,
        api_key: str,
        endpoint: str,
        service_name: str,
        service_version: str,
        debug: bool,
    ):
        self.api_key = api_key
        self.endpoint = endpoint
        self.service_name = service_name
        self.debug = debug

        resource = Resource.create(
            {
                "service.name": service_name,
                "service.version": service_version,
                "agentops.sdk.version": "0.1.0",
            }
        )

        provider = TracerProvider(resource=resource)

        export_url = f"{endpoint}/v1/traces" if not endpoint.endswith("/v1/traces") else endpoint

        otlp_exporter = OTLPSpanExporter(
            endpoint=export_url,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        if debug:
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
            logger.setLevel(logging.DEBUG)
            logger.debug("AgentOps SDK iniciado em modo debug")
            logger.debug("Enviando traces para: %s", export_url)

        trace.set_tracer_provider(provider)
        self._provider = provider

    def tracer(self, name: str = "agentops"):
        return trace.get_tracer(name)

    def shutdown(self):
        self._provider.shutdown()

def init(
    api_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    service_name: str = "ai-agent",
    service_version: str = "0.0.0",
    debug: bool = False,
) -> AgentOpsClient:
    global _client

    resolved_key = get_api_key(api_key)
    resolved_endpoint = get_endpoint(endpoint)

    _client = AgentOpsClient(
        api_key=resolved_key,
        endpoint=resolved_endpoint,
        service_name=service_name,
        service_version=service_version,
        debug=debug,
    )

    logger.info("AgentOps inicializado. Service: %s | Endpoint: %s", service_name, resolved_endpoint)
    return _client

def get_client() -> AgentOpsClient:
    if _client is None:
        raise RuntimeError(
            "AgentOps não foi inicializado. Chame `agentops.init()` antes de usar o SDK."
        )
    return _client