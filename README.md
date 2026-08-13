# QB Protocol - Hosted API & SDK Documentation

## Overview

QB Protocol provides a unified daemon, cross-platform server, reality stabilizers, dream engine, and node service package. The hosted API exposes all functionality over HTTP with self-feeding healing, IP geolocation, and comprehensive monitoring integrations.

## Quick Start

```bash
cd /Users/jjmarte/delta-stream/qb_protocol
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python server/run_server.py
```

Server starts on `http://0.0.0.0:17760`.

## API Endpoints

### Health & Status
- `GET /health` - Health check with Prometheus metrics
- `GET /metrics` - Prometheus metrics endpoint
- `GET /status` - Full system status

### Instances
- `POST /instances` - Create instance
- `POST /instances/{instance_id}/start` - Start instance
- `POST /instances/{instance_id}/stop` - Stop instance

### Cores
- `POST /cores` - Register core
- `POST /cores/{core_id}/heartbeat` - Core heartbeat with load/temperature

### Dream Engine
- `POST /dream/layers` - Create dream layer
- `GET /dream/status` - Dream engine status

### Stabilizers
- `GET /stabilizer/status` - Reality stabilizer status

### IP Geolocation (No-Login Quick Connect)
- `POST /ip/lookup` - IP geolocation lookup
  - Body: `{"ip": "optional_ip", "provider": "ip-api|ipdata|ipify|freegeoip"}`
- `GET /ip/quick-connect` - Quick connect no-login IP lookup

### Healing & Regen
- `POST /healing/regen` - Trigger regeneration cycle
- `GET /healing/status` - Healing system status

### Monitor Integration (Mirror Methodology)
- `POST /monitor/integrate?mirror_url=<url>` - Integrate with external mirror

### SDK Boilerplate
- `POST /sdk/python` - Get Python SDK code snippet
- `POST /sdk/javascript` - Get JavaScript SDK code snippet

## IP Geolocation Providers

| Provider | Login Required | Accuracy | Notes |
|----------|---------------|----------|-------|
| IP-API | No | City ~45% | Fast, no auth |
| Ipify | No | Basic | Returns public IP only |
| FreeGeoIP | No | City | Stricter rate limits |
| IPdata | Yes | High | Comprehensive data |
| IPGeolocation.io | Yes | High | Minimal setup |

## Monitoring Integrations

### Error Tracking
- **Sentry** - Set `SENTRY_DSN` env var. Captures exceptions with breadcrumbs.

### Metrics
- **Prometheus** - `/metrics` endpoint exposes:
  - `qb_requests_total` - Request count by method/endpoint/status
  - `qb_request_latency_seconds` - Request latency histogram
  - `qb_active_instances` - Active instance gauge
  - `qb_active_cores` - Active core gauge
  - `qb_dream_convergence` - Dream convergence gauge
  - `qb_singularity_risk` - Singularity risk gauge
  - `qb_global_coherence` - Global coherence gauge

### APM / Observability
- **Datadog** - Add Datadog APM library and configure `DD_SERVICE`, `DD_ENV`
- **New Relic** - Add `newrelic` agent and configure license key
- **Dynatrace** - Add OneAgent SDK for Python
- **CubeAPM** - Integrate with Python logging via `cube_apm` package
- **SigNoz** - Export to OTLP endpoint: `OTEL_EXPORTER_OTLP_ENDPOINT`
- **Middleware** - Auto-instrument with Middleware Python SDK
- **Apitally** - Add `apitally` wrapper around FastAPI app

## Python SDK

```python
from qb_protocol.sdk.python_sdk import QBProtocolClient

client = QBProtocolClient("http://localhost:17760")

# Status
print(client.status())

# Create instance
print(client.create_instance("my-instance"))

# Quick IP lookup (no login)
print(client.quick_ip())

# IP lookup with specific provider
print(client.ip_lookup(ip="8.8.8.8", provider="ip-api"))

# Dream layers
print(client.create_dream_layer(depth=0.5, projection={"type": "test"}))

# Healing
print(client.trigger_regen())
```

## JavaScript SDK

```javascript
const { QBProtocolClient } = require('./sdk/javascript_sdk.js');

const client = new QBProtocolClient("http://localhost:17760");

// Status
client.status().then(console.log);

// Create instance
client.createInstance("my-instance").then(console.log);

// Quick IP lookup (no login)
client.quickIP().then(console.log);

// IP lookup with specific provider
client.ipLookup("8.8.8.8", "ip-api").then(console.log);

// Dream layers
client.createDreamLayer(0.5, {type: "test"}).then(console.log);

// Healing
client.triggerRegen().then(console.log);
```

## Self-Feeding Healing & Regen

The IPSelfHealingSystem runs a background loop every 30 seconds:
- Detects failed instances
- Attempts resurrection via regen cycle
- Logs healing actions to history
- Exposes `/healing/regen` and `/healing/status`

## Mirror Methodology Integration

```python
from qb_protocol.server.monitor_integration import monitor_integration

monitor_integration.mirror_url = "http://mirror-host:8080"
monitor_integration.start()
```

The monitor integration polls all stabilizer, dream, and daemon status every second and pushes to the mirror URL, maintaining the same bidirectional sync pattern as the render-space- <-> Genie-twin virtual mirror.

## Rate Limiting

Default rules:
- Global: 1000 calls / 60s, burst 50
- Instance: 200 calls / 60s, burst 20
- Dream engine: 500 calls / 60s, burst 30

Custom rules can be added via `rate_limiter.add_rule()`.
