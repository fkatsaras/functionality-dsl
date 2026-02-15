# FDSL Examples

Working examples showing REST APIs, WebSocket streams, authentication, and data transformations.

## Quick Start

```bash
cd examples/smart-home
fdsl generate main.fdsl --out generated
cd generated && docker compose -p <PROJECT-NAME> up
```

## Examples

- **smart-home** - REST API basics, multi-source aggregation
- **ecommerce** - Full app with auth, CRUD, WebSocket orders
- **finnhub** - External API integration with query params
- **weather-comparison** - Multi-source data, transformations
- **health-monitoring** - WebSocket streams, real-time data
- **air-quality** - API integration, computed fields
- **m2m** - Machine-to-machine communication

## Dummy Services

Some examples need a local service. Start with:

```bash
cd examples/user-management
bash run.sh
```

Examples using public APIs (Wikipedia, Binance, weather) need no setup.

## Cleanup

```bash
docker compose -p <PROJECT-NAME> down   # Stop app
bash scripts/cleanup.sh          # Full cleanup
```
