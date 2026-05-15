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
