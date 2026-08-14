#!/usr/bin/env python3
"""
QB Protocol - Natural Systems API Routes
Research catalog: taxa, compounds, publications, products.
"""

from fastapi import APIRouter, Body, Request, UploadFile, File
from fastapi.responses import JSONResponse, RedirectResponse
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import asdict

try:
    from qb_protocol.natural_systems.catalog import natural_catalog
    HAS_NATURAL_SYSTEMS = True
except ImportError:
    try:
        from natural_systems.catalog import natural_catalog
        HAS_NATURAL_SYSTEMS = True
    except ImportError:
        HAS_NATURAL_SYSTEMS = False

router = APIRouter(prefix="/natural-systems", tags=["natural-systems"])


@router.get("/health")
def natural_health():
    return {"status": "ok", "catalog": "active"}


@router.get("/stats")
def catalog_stats():
    if not HAS_NATURAL_SYSTEMS:
        return {"error": "natural_systems_unavailable"}
    return natural_catalog.get_stats()


@router.get("/taxa/search")
def search_taxa(q: str = "", limit: int = 50):
    if not HAS_NATURAL_SYSTEMS:
        return {"error": "natural_systems_unavailable"}
    if not q:
        return {"error": "query_required"}
    results = natural_catalog.search_taxa(q, limit=limit)
    return {"query": q, "results": results}


@router.get("/compounds/search")
def search_compounds(q: str = "", limit: int = 50):
    if not HAS_NATURAL_SYSTEMS:
        return {"error": "natural_systems_unavailable"}
    if not q:
        return {"error": "query_required"}
    results = natural_catalog.search_compounds(q, limit=limit)
    return {"query": q, "results": results}


@router.get("/publications/search")
def search_publications(q: str = "", limit: int = 50):
    if not HAS_NATURAL_SYSTEMS:
        return {"error": "natural_systems_unavailable"}
    if not q:
        return {"error": "query_required"}
    results = natural_catalog.search_publications(q, limit=limit)
    return {"query": q, "results": results}


@router.get("/products/search")
def search_products(q: str = "", limit: int = 50):
    if not HAS_NATURAL_SYSTEMS:
        return {"error": "natural_systems_unavailable"}
    if not q:
        return {"error": "query_required"}
    results = natural_catalog.search_products(q, limit=limit)
    return {"query": q, "results": results}


@router.post("/taxa/import-xml")
def import_taxa_xml(file: UploadFile = File(...)):
    if not HAS_NATURAL_SYSTEMS:
        return {"error": "natural_systems_unavailable"}
    temp_path = Path("/tmp") / f"taxa_import_{uuid.uuid4().hex}.xml"
    try:
        content = file.file.read()
        temp_path.write_bytes(content)
        result = natural_catalog.import_xml(temp_path)
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        if temp_path.exists():
            temp_path.unlink()


@router.get("/taxa/export-xml")
def export_taxa_xml():
    if not HAS_NATURAL_SYSTEMS:
        return {"error": "natural_systems_unavailable"}
    output_path = Path.home() / ".qb_protocol_natural_catalog_export.xml"
    result = natural_catalog.export_xml(output_path)
    return result


@router.get("/sources")
def get_sources():
    return {
        "sources": [
            {"name": "GBIF", "url": "https://api.gbif.org/v1/", "description": "Global Biodiversity Information Facility"},
            {"name": "PubChem", "url": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/", "description": "PubChem PUG REST"},
            {"name": "Europe PMC", "url": "https://www.ebi.ac.uk/europepmc/webservices/rest/", "description": "Europe PMC API"},
            {"name": "ChEBI", "url": "https://www.ebi.ac.uk/chebi/", "description": "Chemical Entities of Biological Interest"},
            {"name": "OpenAlex", "url": "https://docs.openalex.org/", "description": "Open publication metadata"},
            {"name": "Plants of the World Online", "url": "https://powo.science.kew.org/", "description": "Kew botanical taxonomy"},
        ]
    }


@router.get("/")
def natural_root():
    return RedirectResponse(url="/natural-systems/health")
