# Siri Integration Release Notes

## Version 2.0.0 — Native Human Conversation Model

### What's New

- **Model-first conversation**: Siri uses the local GPT model for all chat responses. The model owns the conversation.
- **Short prompts, short memory**: Only the last 2 conversation turns are kept in context. Prompts are kept minimal to stay within the model's 512-token context window.
- **Self-correcting output**: If the model refuses or exceeds its threshold, it self-corrects within its own generation. No external override hacks.
- **Store as tool catalog**: The cloud-backed store handles system intents (execute, control, reminder, image, sleep, learn, private) with consistent, fast, offline-capable replies.
- **Private mode**: Secure intents bypass the cloud and model entirely. Local-only execution.
- **Offline fallback**: Works without internet. Local cache + hardcoded responses ensure Siri always responds.

### Design Principles

- **Consistency over speed**: The model doesn't have to be fast. It just has to be consistent.
- **Partitioned temp state**: Conversation history is capped at 2 turns. No context bloat.
- **Model as mind**: The model's base training + short system prompt is enough. No complex token parsing or generation markers.
- **Virtual match**: If the model exceeds its constraints, it self-corrects or falls back to "I'm on it."

### Stability

- Eliminated "I'm not sure I understand" and other model artifacts.
- Refusals are intercepted and replaced with "I'm on it."
- No heavy JSON parsing. Plain text in, plain text out.

### Requirements

- macOS 15+ / iOS 18+
- QB Protocol server running on localhost:17760
- Optional: S3 bucket for cloud response sync

### Configuration

- `SIRI_RESPONSES_S3_BUCKET` — S3 bucket name
- `SIRI_RESPONSES_S3_KEY` — Object key (default: `siri/responses.json`)
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ENDPOINT_URL`
