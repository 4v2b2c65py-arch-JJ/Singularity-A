#!/usr/bin/env python3
"""
QB Protocol - Natural Systems Catalog
Research catalog with official public API adapters.
SQLite-backed, lightweight, provenance-first.
"""

from __future__ import annotations

import os
import sys
import time
import uuid
import json
import logging
import threading
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.natural_systems.catalog")


DB_PATH = Path.home() / ".qb_protocol_natural_catalog.db"


@dataclass
class Taxon:
    id: Optional[int] = None
    scientific_name: str = ""
    common_name: Optional[str] = None
    rank: Optional[str] = None
    kingdom: Optional[str] = None
    family: Optional[str] = None
    genus: Optional[str] = None
    species: Optional[str] = None
    habitat: Optional[str] = None
    biome: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    source: str = ""
    source_id: Optional[str] = None
    license: Optional[str] = None
    retrieved_at: str = ""


@dataclass
class Compound:
    id: Optional[int] = None
    name: str = ""
    pubchem_cid: Optional[str] = None
    formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    inchikey: Optional[str] = None
    chebi_id: Optional[str] = None
    role: Optional[str] = None
    warning: Optional[str] = None
    source: str = ""
    retrieved_at: str = ""


@dataclass
class Publication:
    id: Optional[int] = None
    title: str = ""
    abstract: Optional[str] = None
    authors: Optional[str] = None
    journal: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    topic: Optional[str] = None
    source: str = ""
    retrieved_at: str = ""


@dataclass
class Product:
    id: Optional[int] = None
    product_name: str = ""
    active_ingredients: Optional[str] = None
    declared_strength: Optional[str] = None
    country: Optional[str] = None
    regulatory_status: Optional[str] = None
    source_url: Optional[str] = None
    warning: Optional[str] = None
    source: str = ""
    retrieved_at: str = ""


class NaturalCatalog:
    """Lightweight natural systems research catalog."""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS taxa (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scientific_name TEXT NOT NULL,
                    common_name TEXT,
                    rank TEXT,
                    kingdom TEXT,
                    family TEXT,
                    genus TEXT,
                    species TEXT,
                    habitat TEXT,
                    biome TEXT,
                    latitude REAL,
                    longitude REAL,
                    source TEXT NOT NULL,
                    source_id TEXT,
                    license TEXT,
                    retrieved_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS compounds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    pubchem_cid TEXT,
                    formula TEXT,
                    molecular_weight REAL,
                    inchikey TEXT,
                    chebi_id TEXT,
                    role TEXT,
                    warning TEXT,
                    source TEXT NOT NULL,
                    retrieved_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS publications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    abstract TEXT,
                    authors TEXT,
                    journal TEXT,
                    year INTEGER,
                    doi TEXT,
                    pmid TEXT,
                    pmcid TEXT,
                    topic TEXT,
                    source TEXT NOT NULL,
                    retrieved_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_name TEXT NOT NULL,
                    active_ingredients TEXT,
                    declared_strength TEXT,
                    country TEXT,
                    regulatory_status TEXT,
                    source_url TEXT,
                    warning TEXT,
                    source TEXT NOT NULL,
                    retrieved_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    description TEXT,
                    license TEXT,
                    enabled INTEGER DEFAULT 1,
                    last_sync TEXT
                );
            """)

    def _now(self) -> str:
        return datetime.utcnow().isoformat() + "Z"

    def search_taxa(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM taxa
                WHERE scientific_name LIKE ? OR common_name LIKE ?
                LIMIT ?
                """,
                (f"%{query}%", f"%{query}%", limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def search_compounds(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM compounds
                WHERE name LIKE ? OR formula LIKE ? OR pubchem_cid LIKE ?
                LIMIT ?
                """,
                (f"%{query}%", f"%{query}%", f"%{query}%", limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def search_publications(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM publications
                WHERE title LIKE ? OR abstract LIKE ? OR topic LIKE ?
                LIMIT ?
                """,
                (f"%{query}%", f"%{query}%", f"%{query}%", limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def search_products(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM products
                WHERE product_name LIKE ? OR active_ingredients LIKE ?
                LIMIT ?
                """,
                (f"%{query}%", f"%{query}%", limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def insert_taxon(self, taxon: Taxon) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO taxa (scientific_name, common_name, rank, kingdom, family, genus, species,
                habitat, biome, latitude, longitude, source, source_id, license, retrieved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    taxon.scientific_name, taxon.common_name, taxon.rank, taxon.kingdom,
                    taxon.family, taxon.genus, taxon.species, taxon.habitat, taxon.biome,
                    taxon.latitude, taxon.longitude, taxon.source, taxon.source_id,
                    taxon.license, taxon.retrieved_at or self._now(),
                ),
            )
            return cursor.lastrowid

    def insert_compound(self, compound: Compound) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO compounds (name, pubchem_cid, formula, molecular_weight, inchikey, chebi_id, role, warning, source, retrieved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    compound.name, compound.pubchem_cid, compound.formula,
                    compound.molecular_weight, compound.inchikey, compound.chebi_id,
                    compound.role, compound.warning, compound.source,
                    compound.retrieved_at or self._now(),
                ),
            )
            return cursor.lastrowid

    def insert_publication(self, publication: Publication) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO publications (title, abstract, authors, journal, year, doi, pmid, pmcid, topic, source, retrieved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    publication.title, publication.abstract, publication.authors,
                    publication.journal, publication.year, publication.doi,
                    publication.pmid, publication.pmcid, publication.topic,
                    publication.source, publication.retrieved_at or self._now(),
                ),
            )
            return cursor.lastrowid

    def insert_product(self, product: Product) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO products (product_name, active_ingredients, declared_strength, country, regulatory_status, source_url, warning, source, retrieved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product.product_name, product.active_ingredients, product.declared_strength,
                    product.country, product.regulatory_status, product.source_url,
                    product.warning, product.source, product.retrieved_at or self._now(),
                ),
            )
            return cursor.lastrowid

    def import_xml(self, xml_path: Path) -> Dict[str, Any]:
        """Import taxa from XML file using ElementTree."""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            imported = {"taxa": 0, "compounds": 0, "publications": 0, "products": 0}
            
            for item in root.findall("taxon"):
                taxon = Taxon(
                    scientific_name=item.findtext("scientific_name", ""),
                    common_name=item.findtext("common_name", ""),
                    rank=item.findtext("rank", ""),
                    kingdom=item.findtext("kingdom", ""),
                    family=item.findtext("family", ""),
                    genus=item.findtext("genus", ""),
                    species=item.findtext("species", ""),
                    habitat=item.findtext("habitat", ""),
                    biome=item.findtext("biome", ""),
                    source=item.findtext("source", "xml_import"),
                    retrieved_at=self._now(),
                )
                self.insert_taxon(taxon)
                imported["taxa"] += 1
            
            return {"status": "ok", "imported": imported}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def export_xml(self, output_path: Path) -> Dict[str, Any]:
        """Export catalog to XML."""
        try:
            root = ET.Element("catalog")
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("SELECT * FROM taxa LIMIT 1000").fetchall()
                for row in rows:
                    taxon_el = ET.SubElement(root, "taxon")
                    for key in row.keys():
                        el = ET.SubElement(taxon_el, key)
                        el.text = str(row[key]) if row[key] is not None else ""
            
            tree = ET.ElementTree(root)
            tree.write(output_path, encoding="utf-8", xml_declaration=True)
            return {"status": "ok", "path": str(output_path)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            for table in ["taxa", "compounds", "publications", "products"]:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                stats[table] = count
            return stats


natural_catalog = NaturalCatalog()
