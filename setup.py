from setuptools import setup, find_packages

setup(
    name="agent_tracer_sdk",
    version="0.1.0",
    description="Observability SDK for AI Agents",
    packages=find_packages(),
    install_requires=[
        "opentelemetry-api>=1.20.0",
        "opentelemetry-sdk>=1.20.0",
        "opentelemetry-exporter-otlp>=1.20.0",
        "opentelemetry-exporter-gcp-trace>=1.6.0",
        "opentelemetry-exporter-gcp-monitoring>=1.6.0",
        "google-cloud-logging>=3.8.0",
        "opentelemetry-instrumentation-google-genai>=0.7b0",
        "requests>=2.31.0"
    ],
)
