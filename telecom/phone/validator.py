#!/usr/bin/env python3
"""
QB Protocol - Phone Number Validation
Global phone number parsing and validation using phonenumbers library.
"""

import os
import time
import uuid
import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.telecom.phone")

try:
    import phonenumbers
    from phonenumbers import carrier, geocoder, timezone
    HAS_PHONENUMBERS = True
except ImportError:
    HAS_PHONENUMBERS = False
    LOG.warning("phonenumbers not installed. Phone validation disabled.")


@dataclass
class PhoneInfo:
    original: str
    e164: str
    country: str
    country_code: str
    national_number: str
    carrier: str
    region: str
    timezones: List[str]
    valid: bool
    metadata: Dict[str, Any]


class PhoneValidator:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent / "qb_protocol_telecom_phones.json"):
        self.state_path = state_path
        self.phones: Dict[str, PhoneInfo] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for pid, p in data.get("phones", {}).items():
                        self.phones[pid] = PhoneInfo(**p)
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "phones": {pid: asdict(p) for pid, p in self.phones.items()}
                }, f, indent=2, default=str)
        except Exception:
            pass

    def validate(self, phone_str: str, region: Optional[str] = None) -> PhoneInfo:
        if not HAS_PHONENUMBERS:
            return PhoneInfo(
                original=phone_str,
                e164=phone_str,
                country="",
                country_code="",
                national_number=phone_str,
                carrier="",
                region="",
                timezones=[],
                valid=False,
                metadata={"error": "phonenumbers not installed"},
            )

        try:
            parsed = phonenumbers.parse(phone_str, region)
            valid = phonenumbers.is_valid_number(parsed)
            country = phonenumbers.region_code_for_number(parsed) or ""
            carrier_name = carrier.name_for_number(parsed, "en") or ""
            region_name = geocoder.description_for_number(parsed, "en") or ""
            tz = timezone.time_zones_for_number(parsed) or []
            e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164) if valid else phone_str
            national = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL) if valid else phone_str

            info = PhoneInfo(
                original=phone_str,
                e164=e164,
                country=country,
                country_code=str(parsed.country_code),
                national_number=national,
                carrier=carrier_name,
                region=region_name,
                timezones=tz,
                valid=valid,
                metadata={},
            )

            with self._lock:
                self.phones[info.e164] = info
            self._save()
            return info
        except Exception as e:
            info = PhoneInfo(
                original=phone_str,
                e164=phone_str,
                country="",
                country_code="",
                national_number=phone_str,
                carrier="",
                region="",
                timezones=[],
                valid=False,
                metadata={"error": str(e)},
            )
            with self._lock:
                self.phones[phone_str] = info
            self._save()
            return info

    def get_phones(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(p) for p in self.phones.values()]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_phones": len(self.phones),
                "valid_phones": len([p for p in self.phones.values() if p.valid]),
                "phonenumbers_available": HAS_PHONENUMBERS,
            }


phone_validator = PhoneValidator()
