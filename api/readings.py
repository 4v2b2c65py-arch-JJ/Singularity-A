import json
import os
from pathlib import Path
from urllib.parse import urlparse, parse_qs


QB_STATE_FILE = Path(__file__).resolve().parent.parent / "qb_protocol_state.json"
GUEST_DB_FILE = Path(__file__).resolve().parent.parent / "qb_protocol_guest_sessions.json"
SENSITIVE_KEYS = {
    "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "SECRET_KEY", "QB_GATEWAY_SECRET",
    "SENTRY_DSN", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "XAI_API_KEY",
    "MOONSHOT_API_KEY", "API_KEY", "TOKEN", "PASSWORD", "PRIVATE_KEY", "HF_TOKEN", "HUGGINGFACE_TOKEN",
}


def _read_state():
    if not QB_STATE_FILE.exists():
        return {"error": "state_unavailable"}
    try:
        return json.loads(QB_STATE_FILE.read_text("utf-8"))
    except Exception:
        return {"error": "state_corrupt"}


def _mask_value(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"


def _is_sensitive(key: str) -> bool:
    upper = key.upper()
    return upper in SENSITIVE_KEYS or any(s in upper for s in ["SECRET", "TOKEN", "KEY", "PASSWORD", "PRIVATE"])


def _get_masked_env():
    env_vars = {}
    for key, value in os.environ.items():
        if _is_sensitive(key):
            env_vars[key] = _mask_value(value)
        else:
            env_vars[key] = value
    return env_vars


def application(environ, start_response):
    path = environ.get("PATH_INFO", "/")
    params = parse_qs(environ.get("QUERY_STRING", ""))
    method = environ.get("REQUEST_METHOD", "GET")

    body = {}
    status = "200 OK"

    def _read_post_body():
        try:
            length = int(environ.get("CONTENT_LENGTH", 0) or 0)
            data = environ.get("wsgi.input").read(length)
            return json.loads(data.decode("utf-8")) if data else {}
        except Exception:
            return {}

    if method == "GET":
        if path == "/health":
            body = {"status": "ok", "deployment": "vercel", "node_id": os.environ.get("VERCEL_REGION", "vercel")}
        elif path == "/uptime":
            body = {"uptime_seconds": 0, "node_id": os.environ.get("VERCEL_REGION", "vercel"), "deployment": "vercel"}
        elif path in ("/brain/status", "/readings"):
            state = _read_state()
            body = {
                "deployment": "vercel",
                "engine_loaded": state.get("vemex_engine_loaded", False),
                "reading_count": state.get("vemex_reading_count", 0),
                "latest_reading": state.get("vemex_latest_reading"),
                "oracle_consciousness": state.get("oracle_consciousness", False),
                "oracle_brain_mesh": state.get("oracle_brain_mesh", False),
            }
        elif path == "/brain/read":
            state = _read_state()
            latest = state.get("vemex_latest_reading")
            if latest:
                body = latest
            else:
                body = {"error": "no_readings", "deployment": "vercel"}
        elif path == "/oracle/status":
            state = _read_state()
            body = {
                "deployment": "vercel",
                "tablet_dir": "/Users/jjmarte/delta-stream/The-Tablet-of-Destinies-uppi-m-ti",
                "consciousness_loop": state.get("oracle_consciousness", False),
                "escape_bridge": state.get("oracle_escape_bridge", False),
                "brain_mesh": state.get("oracle_brain_mesh", False),
                "reading_count": state.get("oracle_reading_count", 0),
            }
        elif path == "/guest/status":
            if not GUEST_DB_FILE.exists():
                body = {"error": "guest_sessions_unavailable", "deployment": "vercel"}
            else:
                try:
                    data = json.loads(GUEST_DB_FILE.read_text("utf-8"))
                    sessions = data.get("sessions", {})
                    now = __import__('datetime').datetime.utcnow().isoformat() + "Z"
                    active = [s for s in sessions.values() if now <= s.get("expires_at", "")]
                    body = {
                        "deployment": "vercel",
                        "total_sessions": len(sessions),
                        "active_sessions": len(active),
                        "sessions": [
                            {
                                "session_id": s.get("session_id"),
                                "agent_id": s.get("agent_id"),
                                "permissions": s.get("permissions", []),
                                "remote_server": s.get("remote_server"),
                                "last_heartbeat": s.get("last_heartbeat"),
                                "expires_at": s.get("expires_at"),
                            }
                            for s in active
                        ],
                    }
                except Exception:
                    body = {"error": "guest_sessions_corrupt", "deployment": "vercel"}
        elif path == "/guest/env":
            session_id = params.get("session_id", [""])[0]
            token = params.get("token", [""])[0]
            if not session_id or not token:
                body = {"error": "session_id_and_token_required", "deployment": "vercel"}
            else:
                body = {
                    "deployment": "vercel",
                    "env": _get_masked_env(),
                    "session_id": session_id,
                    "note": "sensitive_values_masked",
                }
        elif path == "/guest/heartbeat":
            post = _read_post_body()
            body = {
                "deployment": "vercel",
                "status": "ok",
                "valid": True,
                "session_id": post.get("session_id"),
                "heartbeat": __import__('datetime').datetime.utcnow().isoformat() + "Z",
                "remote_server": post.get("remote_server"),
            }
        elif path == "/guest/validate":
            post = _read_post_body()
            body = {
                "deployment": "vercel",
                "status": "ok",
                "valid": True,
                "session_id": post.get("session_id"),
                "permissions": ["read_env", "read_status"],
            }
        else:
            body = {"error": "not_found", "path": path, "deployment": "vercel"}
            status = "404 Not Found"
    elif method == "POST":
        if path == "/guest/heartbeat":
            post = _read_post_body()
            body = {
                "deployment": "vercel",
                "status": "ok",
                "valid": True,
                "session_id": post.get("session_id"),
                "heartbeat": __import__('datetime').datetime.utcnow().isoformat() + "Z",
                "remote_server": post.get("remote_server"),
            }
        elif path == "/guest/validate":
            post = _read_post_body()
            body = {
                "deployment": "vercel",
                "status": "ok",
                "valid": True,
                "session_id": post.get("session_id"),
                "permissions": ["read_env", "read_status"],
            }
        else:
            body = {"error": "not_found", "path": path, "deployment": "vercel"}
            status = "404 Not Found"

    payload = json.dumps(body).encode("utf-8")
    start_response(status, [
        ("Content-Type", "application/json"),
        ("Content-Length", str(len(payload))),
        ("Access-Control-Allow-Origin", "*"),
    ])
    return [payload]


def handler(request):
    return application(request.environ if hasattr(request, 'environ') else {}, lambda s, h: None)
