import json
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult


class CleanConsoleExporter(SpanExporter):
    """Imprime spans no console com apenas os campos do AgentTracer."""

    def export(self, spans):
        for span in spans:
            attrs = dict(span.attributes) if span.attributes else {}
            kind = attrs.get("agent_tracer.kind", "unknown")

            record = {
                "trace_id": format(span.context.trace_id, "032x"),
                "span_id": format(span.context.span_id, "016x"),
                "parent_id": format(span.parent.span_id, "016x") if span.parent else None,
                "kind": kind,
                "status": attrs.get("agent_tracer.status", "unknown"),
                "latency_ms": attrs.get("agent_tracer.latency_ms", 0),
                "timestamp": attrs.get("agent_tracer.timestamp", ""),
            }

            # Campos por tipo
            if kind == "agent":
                record["agent_name"] = attrs.get("agent_tracer.agent_name", "")
                record["prompt"] = attrs.get("agent_tracer.prompt", "")
                record["completion"] = attrs.get("agent_tracer.completion", "")

            elif kind == "tool":
                record["tool_name"] = attrs.get("agent_tracer.tool_name", "")
                record["tool_input"] = attrs.get("agent_tracer.tool_input", "")
                record["tool_output"] = attrs.get("agent_tracer.tool_output", "")

            elif kind == "llm":
                record["prompt"] = attrs.get("agent_tracer.prompt", "")
                record["completion"] = attrs.get("agent_tracer.completion", "")
                record["model"] = attrs.get("agent_tracer.model", "")
                record["provider"] = attrs.get("agent_tracer.provider", "")
                record["input_tokens"] = attrs.get("agent_tracer.input_tokens", 0)
                record["output_tokens"] = attrs.get("agent_tracer.output_tokens", 0)
                record["total_tokens"] = attrs.get("agent_tracer.total_tokens", 0)

            # Campos de erro (se houver)
            if record["status"] == "error":
                record["error_type"] = attrs.get("agent_tracer.error_type", "")
                record["error_message"] = attrs.get("agent_tracer.error_message", "")

            print(json.dumps(record, indent=2, ensure_ascii=False))

        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


class GCPLoggingExporter(SpanExporter):
    """
    Envia os spans como logs estruturados para o Google Cloud Logging.
    Garante que os logs passem pelo Log Router (Sink) e cheguem ao BigQuery.
    """
    def __init__(self, project_id: str = None, log_name: str = "agent-tracer-logs"):
        from google.cloud import logging as gcp_logging
        
        # O cliente automaticamente usa Application Default Credentials
        self.client = gcp_logging.Client(project=project_id) if project_id else gcp_logging.Client()
        self.logger = self.client.logger(log_name)

    def export(self, spans):
        for span in spans:
            attrs = dict(span.attributes) if span.attributes else {}
            kind = attrs.get("agent_tracer.kind", "unknown")

            # Inicia o record com TODAS as chaves possíveis.
            # Isso força o BigQuery a criar o Schema (STRUCT) completo,
            # não importando se o primeiro log a chegar é "unknown", "agent" ou "llm".
            record = {
                "trace_id": format(span.context.trace_id, "032x"),
                "span_id": format(span.context.span_id, "016x"),
                "parent_id": format(span.parent.span_id, "016x") if span.parent else None,
                "kind": kind,
                "status": attrs.get("agent_tracer.status", "unknown"),
                "latency_ms": attrs.get("agent_tracer.latency_ms", 0),
                "timestamp": attrs.get("agent_tracer.timestamp", ""),
                "agent_name": "",
                "prompt": "",
                "completion": "",
                "tool_name": "",
                "tool_input": "",
                "tool_output": "",
                "model": "",
                "provider": "",
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "error_type": "",
                "error_message": "",
            }

            if kind == "agent":
                record["agent_name"] = attrs.get("agent_tracer.agent_name", "")
                record["prompt"] = attrs.get("agent_tracer.prompt", "")
                record["completion"] = attrs.get("agent_tracer.completion", "")
            elif kind == "tool":
                record["tool_name"] = attrs.get("agent_tracer.tool_name", "")
                record["tool_input"] = attrs.get("agent_tracer.tool_input", "")
                record["tool_output"] = attrs.get("agent_tracer.tool_output", "")
            elif kind == "llm":
                record["prompt"] = attrs.get("agent_tracer.prompt", "")
                record["completion"] = attrs.get("agent_tracer.completion", "")
                record["model"] = attrs.get("agent_tracer.model", "")
                record["provider"] = attrs.get("agent_tracer.provider", "")
                record["input_tokens"] = attrs.get("agent_tracer.input_tokens", 0)
                record["output_tokens"] = attrs.get("agent_tracer.output_tokens", 0)
                record["total_tokens"] = attrs.get("agent_tracer.total_tokens", 0)

            if record["status"] == "error":
                record["error_type"] = attrs.get("agent_tracer.error_type", "")
                record["error_message"] = attrs.get("agent_tracer.error_message", "")

            # Envia diretamente para o Cloud Logging como JSON Estruturado
            self.logger.log_struct(record)

        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass

class MLFlowAPIExporter(SpanExporter):
    """
    Exportador assíncrono que consolida spans de uma mesma requisição (trace)
    e envia o payload final exatamente no formato esperado pela API do MLflow.
    """
    def __init__(self, api_url: str):
        self.api_url = api_url
        # Cache em memória para agregar dados dos spans filhos (llm, tool) até o agente terminar
        self._trace_cache = {}

    def export(self, spans):
        import requests
        import logging
        logger = logging.getLogger("agent_tracer")

        for span in spans:
            attrs = dict(span.attributes) if span.attributes else {}
            kind = attrs.get("agent_tracer.kind", "unknown")
            trace_id = format(span.context.trace_id, "032x")

            if trace_id not in self._trace_cache:
                self._trace_cache[trace_id] = {"input_tokens": 0, "output_tokens": 0, "tool_output": ""}

            if kind == "llm":
                self._trace_cache[trace_id]["input_tokens"] += int(attrs.get("agent_tracer.input_tokens", 0))
                self._trace_cache[trace_id]["output_tokens"] += int(attrs.get("agent_tracer.output_tokens", 0))
            
            elif kind == "tool":
                tool_name = attrs.get("agent_tracer.tool_name", "tool")
                tool_out = attrs.get("agent_tracer.tool_output", "")
                self._trace_cache[trace_id]["tool_output"] += f"[{tool_name}]: {tool_out}\n"

            elif kind == "agent":
                cache = self._trace_cache.get(trace_id, {})
                
                payload = {
                    "trace_id": trace_id,
                    "run_name": attrs.get("agent_tracer.agent_name", "agent-run"),
                    "tags": {
                        "status": attrs.get("agent_tracer.status", "unknown")
                    },
                    "attributes": {
                        "user_prompt": attrs.get("agent_tracer.prompt", ""),
                        "agent_response": attrs.get("agent_tracer.completion", ""),
                        "agentops_tool_output": cache.get("tool_output", "").strip(),
                        "agentops_duration_ms": float(attrs.get("agent_tracer.latency_ms", 0.0)),
                        "gen_ai_usage_input_tokens": cache.get("input_tokens", 0),
                        "gen_ai_usage_output_tokens": cache.get("output_tokens", 0)
                    }
                }

                try:
                    # Envia o POST assíncrono para a sua API do FastAPI (MLFlow Pipeline)
                    response = requests.post(self.api_url, json=payload, timeout=5.0)
                    response.raise_for_status()
                except Exception as e:
                    logger.warning(f"Falha ao enviar trace para MLflow API ({self.api_url}): {str(e)}")
                
                # Limpa o cache após enviar o payload do agente
                if trace_id in self._trace_cache:
                    del self._trace_cache[trace_id]

        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass
