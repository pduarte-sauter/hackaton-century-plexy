"""
Configuração centralizada do AgentTracer SDK.
"""
import os

# Identidade do serviço
SERVICE_NAME = os.getenv("AGENT_TRACER_SERVICE", "ai-agent")
SERVICE_VERSION = os.getenv("AGENT_TRACER_VERSION", "0.1.0")

#   console - stdout (dev local)
#   cloud   - Google Cloud Trace / Monitoring
#   otlp    - OTLP HTTP genérico (Jaeger, Grafana, etc.)
EXPORT_MODE = os.getenv("AGENT_TRACER_EXPORT", "console")

# OTLP endpoint (usado apenas quando EXPORT_MODE = "otlp")
OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")

# Google Cloud
GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# MLflow
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")