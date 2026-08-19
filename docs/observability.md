# Optional OpenTelemetry tracing

Tracing is disabled by default so the shared core remains lightweight and the
six product CLIs keep identical behavior when observability is not configured.
If OpenTelemetry is unavailable, the telemetry seam silently uses a no-op
tracer: it emits no warning, changes no response, and never hides application
exceptions.

Install the optional packages and enable the seam explicitly:

```bash
poetry install -E otel
export SHARED_LLM_OTEL_ENABLED=true
```

The seam uses the process-global OpenTelemetry tracer provider. Applications
may configure `opentelemetry-sdk` with the OTLP HTTP exporter from the `otel`
extra and set `OTEL_EXPORTER_OTLP_ENDPOINT` to their own Collector. No
Collector or exporter is contacted merely by enabling the seam; without an
SDK provider, the OpenTelemetry API itself remains no-op.

Gateway child processes receive W3C `traceparent` through their environment.
Product entry spans automatically extract that value. Request IDs remain
application identifiers and are recorded alongside, rather than replaced by,
trace IDs.

Only operational metadata belongs in spans: model, task tier, token counts,
latency, product ID, job ID, status, and target type. Prompts, responses,
credentials, tenant/session tokens, file paths, host names, URLs containing
customer assets, and sample contents must never be span attributes.
