#!/usr/bin/env python3
"""
QB Protocol - Iridium SBD Satellite Communication
Real serial-connected modem support. No simulation fallback.
"""

from __future__ import annotations

import os
import time
import uuid
import json
import logging
import threading
import serial
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import IntEnum

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.satellite.iridium")


class ExitCode(IntEnum):
    OK = 0
    ERROR = 1
    TIMEOUT = 2
    REGISTRATION_FAILED = 3
    SIGNAL_LOST = 4
    PAYLOAD_TOO_LARGE = 5
    HARDWARE_ERROR = 6
    SECURITY_VIOLATION = 7
    GOVERNANCE_REJECTED = 8


@dataclass
class SatelliteConfig:
    port: str = "/dev/ttyUSB0"
    baudrate: int = 19200
    timeout: float = 2.0
    registration_timeout: int = 180
    max_payload_bytes: int = 340
    government_assured: bool = True


@dataclass
class SatelliteMessage:
    message_id: str
    payload: bytes
    direction: str
    exit_code: int
    exit_message: str
    signal_quality: int
    registered: bool
    metadata: Dict[str, Any]
    timestamp: str


class IridiumSBD:
    def __init__(self, config: SatelliteConfig):
        self.config = config
        self.ser: Optional[serial.Serial] = None
        self.registered = False
        self.signal_quality = 0
        self._lock = threading.RLock()

    def _connect(self) -> None:
        if self.ser and self.ser.is_open:
            return
        try:
            self.ser = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.config.timeout,
            )
            LOG.info(f"Satellite: connected to {self.config.port}")
        except Exception as e:
            LOG.error(f"Satellite: connection failed: {e}")
            raise

    def close(self) -> None:
        if self.ser and self.ser.is_open:
            self.ser.close()
            LOG.info("Satellite: connection closed")

    def _command(self, text: str, wait: float = 1.0) -> str:
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Serial port not open")
        self.ser.reset_input_buffer()
        self.ser.write((text + "\r").encode("ascii"))
        self.ser.flush()
        time.sleep(wait)
        response = self.ser.read_all().decode("ascii", errors="replace")
        return response

    def check_modem(self) -> Dict[str, Any]:
        try:
            self._connect()
            response = self._command("AT")
            if "OK" in response:
                return {"status": "ok", "response": response, "exit_code": ExitCode.OK}
            return {"status": "error", "response": response, "exit_code": ExitCode.ERROR}
        except Exception as e:
            return {"status": "error", "response": str(e), "exit_code": ExitCode.HARDWARE_ERROR}

    def signal_quality(self) -> int:
        try:
            self._connect()
            response = self._command("AT+CSQ")
            for line in response.splitlines():
                if line.startswith("+CSQ:"):
                    self.signal_quality = int(line.split(":")[1].strip().split(",")[0])
                    return self.signal_quality
        except Exception:
            pass
        return 0

    def wait_for_registration(self) -> Dict[str, Any]:
        try:
            self._connect()
        except Exception as e:
            return {"status": "error", "response": str(e), "exit_code": ExitCode.HARDWARE_ERROR}
        deadline = time.time() + self.config.registration_timeout
        while time.time() < deadline:
            try:
                response = self._command("AT+CIER=1,1,1,1", wait=0.5)
                response += self._command("AT+SBDREG", wait=2.0)
                if "OK" in response and "ERROR" not in response:
                    self.registered = True
                    return {"status": "registered", "response": response, "exit_code": ExitCode.OK}
            except Exception:
                pass
            time.sleep(5)
        return {"status": "timeout", "response": "Registration timeout", "exit_code": ExitCode.TIMEOUT}

    def write_binary_message(self, payload: bytes) -> Dict[str, Any]:
        if len(payload) > self.config.max_payload_bytes:
            return {"status": "error", "exit_code": ExitCode.PAYLOAD_TOO_LARGE}
        try:
            self._connect()
        except Exception as e:
            return {"status": "error", "response": str(e), "exit_code": ExitCode.HARDWARE_ERROR}
        if not self.ser or not self.ser.is_open:
            return {"status": "error", "exit_code": ExitCode.HARDWARE_ERROR}
        self.ser.reset_input_buffer()
        self.ser.write(f"AT+SBDWB={len(payload)}\r".encode("ascii"))
        self.ser.flush()
        prompt = self.ser.read_until(b":")
        if b":" not in prompt:
            return {"status": "error", "exit_code": ExitCode.HARDWARE_ERROR}
        checksum = sum(payload) & 0xFFFF
        self.ser.write(payload)
        self.ser.write(checksum.to_bytes(2, "big"))
        self.ser.flush()
        response = self.ser.read_until(b"\r")
        if b"0" not in response:
            return {"status": "error", "exit_code": ExitCode.ERROR}
        return {"status": "written", "exit_code": ExitCode.OK}

    def send_sbd(self, payload: bytes) -> SatelliteMessage:
        write_result = self.write_binary_message(payload)
        exit_code = write_result.get("exit_code", ExitCode.ERROR)
        if exit_code != ExitCode.OK:
            return SatelliteMessage(
                message_id=str(uuid.uuid4()),
                payload=payload,
                direction="uplink",
                exit_code=exit_code,
                exit_message=write_result.get("status", "write_failed"),
                signal_quality=self.signal_quality,
                registered=self.registered,
                metadata=write_result,
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
        if not self.ser or not self.ser.is_open:
            return SatelliteMessage(
                message_id=str(uuid.uuid4()),
                payload=payload,
                direction="uplink",
                exit_code=ExitCode.HARDWARE_ERROR,
                exit_message="Serial port not open",
                signal_quality=self.signal_quality,
                registered=self.registered,
                metadata={},
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
        self.ser.reset_input_buffer()
        self.ser.write(b"AT+SBDIX\r")
        self.ser.flush()
        time.sleep(20)
        response = self.ser.read_all().decode("ascii", errors="replace")
        if "ERROR" in response:
            exit_code = ExitCode.ERROR
        return SatelliteMessage(
            message_id=str(uuid.uuid4()),
            payload=payload,
            direction="uplink",
            exit_code=exit_code,
            exit_message=response,
            signal_quality=self.signal_quality,
            registered=self.registered,
            metadata={"response": response},
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    def receive_sbd(self) -> SatelliteMessage:
        try:
            self._connect()
        except Exception as e:
            return SatelliteMessage(
                message_id=str(uuid.uuid4()),
                payload=b"",
                direction="downlink",
                exit_code=ExitCode.HARDWARE_ERROR,
                exit_message=str(e),
                signal_quality=self.signal_quality,
                registered=self.registered,
                metadata={},
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
        if not self.ser or not self.ser.is_open:
            return SatelliteMessage(
                message_id=str(uuid.uuid4()),
                payload=b"",
                direction="downlink",
                exit_code=ExitCode.HARDWARE_ERROR,
                exit_message="Serial port not open",
                signal_quality=self.signal_quality,
                registered=self.registered,
                metadata={},
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
        self.ser.reset_input_buffer()
        self.ser.write(b"AT+SBDIX\r")
        self.ser.flush()
        time.sleep(20)
        response = self.ser.read_all().decode("ascii", errors="replace")
        if "ERROR" in response:
            exit_code = ExitCode.ERROR
        else:
            exit_code = ExitCode.OK
        return SatelliteMessage(
            message_id=str(uuid.uuid4()),
            payload=b"",
            direction="downlink",
            exit_code=exit_code,
            exit_message=response,
            signal_quality=self.signal_quality,
            registered=self.registered,
            metadata={"response": response},
            timestamp=datetime.utcnow().isoformat() + "Z",
        )


class IridiumManager:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent / "qb_protocol_satellite_iridium.json"):
        self.state_path = state_path
        self.modems: Dict[str, IridiumSBD] = {}
        self.messages: List[SatelliteMessage] = []
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    self.messages = [SatelliteMessage(**m) for m in data.get("messages", [])]
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "messages": [asdict(m) for m in self.messages[-1000:]]
                }, f, indent=2, default=str)
        except Exception:
            pass

    def register_modem(self, modem_id: str, config: SatelliteConfig) -> IridiumSBD:
        modem = IridiumSBD(config)
        with self._lock:
            self.modems[modem_id] = modem
        return modem

    def send_message(self, modem_id: str, payload: bytes) -> SatelliteMessage:
        with self._lock:
            modem = self.modems.get(modem_id)
        if not modem:
            return SatelliteMessage(
                message_id=str(uuid.uuid4()),
                payload=payload,
                direction="uplink",
                exit_code=ExitCode.ERROR,
                exit_message="Modem not found",
                signal_quality=0,
                registered=False,
                metadata={},
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
        message = modem.send_sbd(payload)
        with self._lock:
            self.messages.append(message)
            if len(self.messages) > 1000:
                self.messages = self.messages[-1000:]
        self._save()
        return message

    def receive_message(self, modem_id: str) -> SatelliteMessage:
        with self._lock:
            modem = self.modems.get(modem_id)
        if not modem:
            return SatelliteMessage(
                message_id=str(uuid.uuid4()),
                payload=b"",
                direction="downlink",
                exit_code=ExitCode.ERROR,
                exit_message="Modem not found",
                signal_quality=0,
                registered=False,
                metadata={},
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
        message = modem.receive_sbd()
        with self._lock:
            self.messages.append(message)
            if len(self.messages) > 1000:
                self.messages = self.messages[-1000:]
        self._save()
        return message

    def get_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(m) for m in self.messages[-limit:]]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_modems": len(self.modems),
                "total_messages": len(self.messages),
                "exit_codes": {code.name: sum(1 for m in self.messages if m.exit_code == code) for code in ExitCode},
            }


iridium_manager = IridiumManager()
