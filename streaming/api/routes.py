#!/usr/bin/env python3
"""
QB Protocol - Streaming API Routes
"""

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional

try:
    from qb_protocol.streaming.catalog import catalog
    from qb_protocol.streaming.menu_fetcher import menu_fetcher
    from qb_protocol.streaming.core.realm import realm_detector
    from qb_protocol.streaming.core.layer import layer_detector
    from qb_protocol.streaming.core.stream_mapper import stream_mapper
    from qb_protocol.streaming.core.grbl_converter import convert_grbl_text, grbl_to_python
    from qb_protocol.streaming.integration import streaming_integration
    HAS_STREAMING = True
except ImportError:
    try:
        from streaming.catalog import catalog
        from streaming.menu_fetcher import menu_fetcher
        from streaming.core.realm import realm_detector
        from streaming.core.layer import layer_detector
        from streaming.core.stream_mapper import stream_mapper
        from streaming.core.grbl_converter import convert_grbl_text, grbl_to_python
        from streaming.integration import streaming_integration
        HAS_STREAMING = True
    except ImportError:
        HAS_STREAMING = False

router = APIRouter(prefix="/streaming", tags=["streaming"])


@router.get("/status")
def streaming_status():
    if not HAS_STREAMING:
        return {"error": "streaming_unavailable"}
    return streaming_integration.get_status()


@router.get("/realms")
def get_realms():
    if not HAS_STREAMING:
        return {"error": "streaming_unavailable"}
    return catalog.get_realms()


@router.post("/realms")
def create_realm(body: Dict[str, Any] = Body(...)):
    if not HAS_STREAMING:
        return {"error": "streaming_unavailable"}
    return streaming_integration.register_realm(
        name=body.get("name", "Unknown Realm"),
        realm_type=body.get("realm_type", "unknown"),
        description=body.get("description", ""),
        metadata=body.get("metadata"),
    )


@router.get("/realms/{realm_id}/layers")
def get_layers(realm_id: str):
    if not HAS_STREAMING:
        return {"error": "streaming_unavailable"}
    return catalog.get_layers(realm_id)


@router.post("/realms/{realm_id}/layers")
def create_layer(realm_id: str, body: Dict[str, Any] = Body(...)):
    if not HAS_STREAMING:
        return {"error": "streaming_unavailable"}
    layer = catalog.create_layer(
        realm_id=realm_id,
        name=body.get("name", "Default Layer"),
        layer_type=body.get("layer_type", "surface"),
        depth=body.get("depth", 0),
        metadata=body.get("metadata"),
    )
    return layer


@router.get("/realms/{realm_id}/sources")
def get_stream_sources(realm_id: str, layer_id: Optional[str] = None):
    if not HAS_STREAMING:
        return {"error": "streaming_unavailable"}
    return catalog.get_stream_sources(realm_id, layer_id)


@router.post("/realms/{realm_id}/sources")
def add_stream_source(realm_id: str, body: Dict[str, Any] = Body(...)):
    if not HAS_STREAMING:
        return {"error": "streaming_unavailable"}
    layer_id = body.get("layer_id", "")
    source = catalog.add_stream_source(
        name=body.get("name", "Unknown Source"),
        url=body.get("url", ""),
        realm_id=realm_id,
        layer_id=layer_id,
        stream_type=body.get("stream_type", "video"),
        quality=body.get("quality", "unknown"),
        language=body.get("language", "en"),
        metadata=body.get("metadata"),
    )
    return source


@router.get("/realms/{realm_id}/catalog")
def get_catalog(realm_id: str, layer_id: Optional[str] = None, limit: int = 100):
    if not HAS_STREAMING:
        return {"error": "streaming_unavailable"}
    return streaming_integration.get_catalog(realm_id, layer_id, limit)


@router.post("/realms/{realm_id}/catalog")
def add_catalog_item(realm_id: str, body: Dict[str, Any] = Body(...)):
    if not HAS_STREAMING:
        return {"error": "streaming_unavailable"}
    layer_id = body.get("layer_id", "")
    item = catalog.add_catalog_item(
        title=body.get("title", "Unknown Title"),
        realm_id=realm_id,
        layer_id=layer_id,
        stream_sources=body.get("stream_sources", []),
        poster=body.get("poster", ""),
        backdrop=body.get("backdrop", ""),
        description=body.get("description", ""),
        year=body.get("year", 0),
        rating=body.get("rating", 0.0),
        genres=body.get("genres", []),
        metadata=body.get("metadata"),
    )
    return item


@router.post("/detect-realm")
def detect_realm(body: Dict[str, Any] = Body(...)):
    if not HAS_STREAMING:
        return {"error": "streaming_unavailable"}
    return streaming_integration.detect_realm(
        name=body.get("name", ""),
        url=body.get("url", ""),
        description=body.get("description", ""),
    )


@router.post("/detect-layer")
def detect_layer(body: Dict[str, Any] = Body(...)):
    if not HAS_STREAMING:
        return {"error": "streaming_unavailable"}
    return streaming_integration.detect_layer(
        realm_id=body.get("realm_id", ""),
        name=body.get("name", ""),
        url=body.get("url", ""),
        description=body.get("description", ""),
    )


@router.post("/select-stream")
def select_stream(body: Dict[str, Any] = Body(...)):
    if not HAS_STREAMING:
        return {"error": "streaming_unavailable"}
    return streaming_integration.select_stream(
        item_id=body.get("item_id", ""),
        realm_id=body.get("realm_id", ""),
        layer_id=body.get("layer_id", ""),
        available_sources=body.get("available_sources", []),
        preferences=body.get("preferences"),
    )


@router.get("/menu")
def get_menu(category: Optional[str] = None, source: Optional[str] = None, limit: int = 100):
    if not HAS_STREAMING:
        return {"error": "streaming_unavailable"}
    items = menu_fetcher.get_items(category, source, limit)
    return {"items": items, "count": len(items)}


@router.post("/menu/fetch")
def fetch_menu(body: Dict[str, Any] = Body(...)):
    if not HAS_STREAMING:
        return {"error": "streaming_unavailable"}
    source_id = body.get("source_id", "")
    return streaming_integration.fetch_menu_from_source(source_id)


@router.get("/menu/sources")
def get_menu_sources():
    if not HAS_STREAMING:
        return {"error": "streaming_unavailable"}
    return menu_fetcher.get_sources()


@router.post("/menu/sources")
def add_menu_source(body: Dict[str, Any] = Body(...)):
    if not HAS_STREAMING:
        return {"error": "streaming_unavailable"}
    source = menu_fetcher.register_source(
        name=body.get("name", "Unknown Source"),
        base_url=body.get("base_url", ""),
        menu_selector=body.get("menu_selector", "nav"),
        fallback_selector=body.get("fallback_selector", "ul.menu"),
        enabled=body.get("enabled", True),
        metadata=body.get("metadata"),
    )
    return source


@router.post("/grbl/convert")
def convert_grbl(body: Dict[str, Any] = Body(...)):
    if not HAS_STREAMING:
        return {"error": "streaming_unavailable"}
    text = body.get("text", "")
    if not text:
        return {"error": "text_required"}
    result = convert_grbl_text(text)
    return result


@router.post("/grbl/to-python")
def grbl_to_python_endpoint(body: Dict[str, Any] = Body(...)):
    if not HAS_STREAMING:
        return {"error": "streaming_unavailable"}
    text = body.get("text", "")
    if not text:
        return {"error": "text_required"}
    python_code = grbl_to_python(text)
    return {"python_code": python_code}
