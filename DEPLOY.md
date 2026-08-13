# QB Protocol Deployment Guide

## Persistent Runtime on macOS

### Install Service
```bash
bash deploy/install_service.sh
```

### Uninstall Service
```bash
bash deploy/uninstall_service.sh
```

### Service Details
- Label: `com.qbprotocol.server`
- Auto-starts on boot/login via `launchd`
- Restarts automatically on failure via `KeepAlive`
- Logs: `~/Library/Logs/qb_protocol_server.out.log` and `.err.log`

### Verify
```bash
launchctl list | grep qbprotocol
curl http://127.0.0.1:17760/health
```

## Vercel Deployment

### Prerequisites
- Vercel account linked to GitHub repo
- GitHub repository secrets:
  - `VERCEL_TOKEN`
  - `VERCEL_ORG_ID`
  - `VERCEL_PROJECT_ID`

### Environment Variables (Vercel Dashboard)
Set these in **Project Settings > Environment Variables**:

| Variable | Environment | Sensitive | Purpose |
|----------|-------------|-----------|---------|
| `QB_GATEWAY_SECRET` | Production | Yes | Gateway entry signature secret |
| `SENTRY_DSN` | Production | Yes | Sentry error tracking |

**Security rules applied:**
- No `NEXT_PUBLIC_` prefixes for secrets (not applicable here, but enforced by pattern)
- Sensitive variables marked as sensitive in Vercel dashboard
- Production secrets scoped to Production only
- Changes require redeployment to apply

### Deploy
```bash
vercel --prod
```

### GitHub Actions (Optional)
Push to `main` triggers `.github/workflows/vercel-deploy.yml`.

**Security hardening in CI:**
- Uses `vercel build --prebuilt` to avoid double builds
- `git.deploymentEnabled: false` in `vercel.json` prevents duplicate deploys
- Secrets referenced as `${{ secrets.VERCEL_TOKEN }}` only
- Environment protection rules can require approval for production

### Security Scans
`.github/workflows/security.yml` runs:
- **Gitleaks** - detects committed secrets
- **Semgrep** - SAST security audit (`p/security-audit` ruleset)

## Frontend Quick Usage

Open `/` on the deployed server or localhost to access the interactive frontend.

Endpoints:
- `GET /` - Frontend quick usage
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `POST /entry/issue` - Issue entry credential
- `POST /entry/validate` - Validate entry signature
- `POST /instances` - Create instance (entry required or rate limited)
- `POST /instances/{id}/start` - Start instance
- `POST /instances/{id}/stop` - Stop instance
- `POST /dream/layers` - Create dream layer
- `GET /dream/status` - Dream engine status
- `GET /stabilizer/status` - Reality stabilizer status
- `POST /ip/quick-connect` - No-login IP geolocation
- `POST /ip/lookup` - IP lookup by provider
- `POST /healing/regen` - Trigger regeneration
- `GET /healing/status` - Healing system status

## Data Management

Backups stored in `qb_data/backups/`. Retention enforced automatically on healing cycles (7 days default).

## Monitoring

- Prometheus metrics at `/metrics`
- Sentry via `SENTRY_DSN` environment variable
- Vercel activity logs via `vercel activity` CLI
