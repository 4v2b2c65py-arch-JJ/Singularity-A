# Siri Integration Release Notes

## Version 1.0.0 — Production Build

### What's New

- **Conversation Model**: Siri now uses the local GPT model for actual conversation. She can discuss topics, answer questions, and maintain context across chat sessions.
- **Cloud Response Store**: System intents (execute, control, reminder, image, sleep, learn) use a cloud-backed response store for consistent, fast, offline-capable replies.
- **3-Tier Fallback**: Store → Model → Hardcoded. Nothing fails silently. If the model is unavailable, the store handles system intents. If the store is unavailable, hardcoded responses take over.
- **Offline Mode**: Works without internet. Local cache + fallback responses ensure Siri always responds.
- **Private Mode**: Secure intents bypass the cloud and model entirely. Local-only execution.

### Stability Improvements

- Eliminated "I'm not sure I understand" and other model artifacts for system intents.
- Model responses are validated before being returned. Malformed JSON is rejected.
- Conversation model uses a constrained prompt to prevent runaway generation.
- Thread-safe response caching with background cloud sync.

### Requirements

- macOS 15+ / iOS 18+
- QB Protocol server running on localhost:17760
- Optional: S3 bucket for cloud response sync (`SIRI_RESPONSES_S3_BUCKET`)

### Configuration

Set these environment variables for cloud sync:
- `SIRI_RESPONSES_S3_BUCKET` — S3 bucket name
- `SIRI_RESPONSES_S3_KEY` — Object key (default: `siri/responses.json`)
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ENDPOINT_URL`

### API

- `POST /siri/session/create` — Create Siri session
- `POST /siri/voice/command` — Send voice command, get structured response
- `GET /siri/status` — Integration status
- `GET /siri/sessions/{id}` — Session details
- `GET /siri/sessions/{id}/messages` — Message history
