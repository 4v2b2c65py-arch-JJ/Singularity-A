#!/usr/bin/env python3
"""
QB Protocol - GRBL Text Converter
Interprets GRBL-like encoded text and converts to executable Python operations.
"""

import os
import sys
import re
import json
import hashlib
import base64
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.grbl_converter")


class GRBLTokenType(Enum):
    COMMAND = "command"
    PARAMETER = "parameter"
    VALUE = "value"
    OPERATOR = "operator"
    IDENTIFIER = "identifier"
    STRING = "string"
    NUMBER = "number"
    SYMBOL = "symbol"


@dataclass
class GRBLToken:
    token_type: str
    value: str
    line: int
    column: int


@dataclass
class GRBLOperation:
    operation_id: str
    command: str
    parameters: Dict[str, Any]
    raw_text: str
    interpreted_python: str
    result: Optional[Dict[str, Any]]
    timestamp: str


class GRBLConverter:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent / "qb_protocol_grbl_conversions.json"):
        self.state_path = state_path
        self.operations: List[GRBLOperation] = []
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    self.operations = [GRBLOperation(**o) for o in data.get("operations", [])]
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "operations": [asdict(o) for o in self.operations[-1000:]]
                }, f, indent=2, default=str)
        except Exception:
            pass

    def tokenize(self, text: str) -> List[GRBLToken]:
        tokens = []
        lines = text.split("\n")
        for line_idx, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            parts = re.split(r"[\s\-\.\,\;\:\/\(\)\=\[\]\{\}]+", line)
            col = 0
            for part in parts:
                if not part:
                    continue
                token_type = self._classify_token(part)
                tokens.append(GRBLToken(
                    token_type=token_type,
                    value=part,
                    line=line_idx,
                    column=col,
                ))
                col += len(part) + 1
        return tokens

    def _classify_token(self, token: str) -> str:
        if token.startswith(";"):
            return GRBLTokenType.COMMAND.value
        if token.startswith("G") or token.startswith("M"):
            return GRBLTokenType.COMMAND.value
        if token.startswith("X") or token.startswith("Y") or token.startswith("Z") or token.startswith("I") or token.startswith("J") or token.startswith("K"):
            return GRBLTokenType.PARAMETER.value
        if token in ["=", "+", "-", "*", "/", "(", ")", "[", "]", "{", "}", ",", ";", ":", ".", "->"]:
            return GRBLTokenType.OPERATOR.value
        if token.replace(".", "").replace("-", "").isdigit():
            return GRBLTokenType.NUMBER.value
        if token.startswith('"') or token.startswith("'"):
            return GRBLTokenType.STRING.value
        if len(token) > 2 and token.isalpha():
            return GRBLTokenType.IDENTIFIER.value
        return GRBLTokenType.SYMBOL.value

    def convert(self, text: str) -> List[GRBLOperation]:
        tokens = self.tokenize(text)
        operations = []
        current_op = None
        python_lines = []

        for token in tokens:
            if token.token_type == GRBLTokenType.COMMAND.value:
                if current_op:
                    current_op.interpreted_python = "\n".join(python_lines)
                    operations.append(current_op)
                current_op = GRBLOperation(
                    operation_id=str(uuid.uuid4()),
                    command=token.value,
                    parameters={},
                    raw_text=text,
                    interpreted_python="",
                    result=None,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                )
                python_lines = [f"# GRBL: {token.value}"]
            elif current_op:
                if token.token_type == GRBLTokenType.PARAMETER.value:
                    python_lines.append(f"param_{token.value.lower()} = None")
                    current_op.parameters[token.value] = None
                elif token.token_type == GRBLTokenType.NUMBER.value:
                    python_lines.append(f"value = {token.value}")
                elif token.token_type == GRBLTokenType.IDENTIFIER.value:
                    python_lines.append(f"# identifier: {token.value}")
                elif token.token_type == GRBLTokenType.SYMBOL.value:
                    if token.value == "=":
                        python_lines.append("=")
                    elif token.value == ".":
                        python_lines.append(".")

        if current_op:
            current_op.interpreted_python = "\n".join(python_lines)
            operations.append(current_op)

        with self._lock:
            self.operations.extend(operations)
            if len(self.operations) > 1000:
                self.operations = self.operations[-1000:]
        self._save()
        return operations

    def interpret_as_python(self, text: str) -> str:
        tokens = self.tokenize(text)
        lines = ["#!/usr/bin/env python3", '"""', "QB Protocol - GRBL Interpreted Script", '"""', ""]
        indent = 0
        last_token = None

        for token in tokens:
            if token.value == ";":
                lines.append(f"{' ' * indent}# {token.value}")
            elif token.value == ".":
                lines.append(f"{' ' * indent}.")
            elif token.value == ",":
                lines.append(f"{' ' * indent},")
            elif token.value == "=":
                lines.append(f"{' ' * indent}=")
            elif token.value == "/":
                lines.append(f"{' ' * indent}/")
            elif token.value == "-":
                lines.append(f"{' ' * indent}-")
            elif token.value == "(":
                lines.append(f"{' ' * indent}(")
                indent += 4
            elif token.value == ")":
                indent = max(0, indent - 4)
                lines.append(f"{' ' * indent})")
            elif token.value == "{":
                lines.append(f"{' ' * indent}{{")
                indent += 4
            elif token.value == "}":
                indent = max(0, indent - 4)
                lines.append(f"{' ' * indent}}}")
            elif token.token_type == GRBLTokenType.COMMAND.value:
                lines.append(f"{' ' * indent}# COMMAND: {token.value}")
            elif token.token_type == GRBLTokenType.PARAMETER.value:
                lines.append(f"{' ' * indent}{token.value.lower()} = None")
            elif token.token_type == GRBLTokenType.IDENTIFIER.value:
                if last_token and last_token.value == ".":
                    lines[-1] = lines[-1] + token.value
                else:
                    lines.append(f"{' ' * indent}{token.value}")
            elif token.token_type == GRBLTokenType.NUMBER.value:
                lines.append(f"{' ' * indent}{token.value}")
            last_token = token

        return "\n".join(lines)

    def execute_interpreted(self, text: str) -> Dict[str, Any]:
        tokens = self.tokenize(text)
        result = {
            "tokens": len(tokens),
            "commands": len([t for t in tokens if t.token_type == GRBLTokenType.COMMAND.value]),
            "parameters": len([t for t in tokens if t.token_type == GRBLTokenType.PARAMETER.value]),
            "identifiers": [t.value for t in tokens if t.token_type == GRBLTokenType.IDENTIFIER.value],
            "numbers": [t.value for t in tokens if t.token_type == GRBLTokenType.NUMBER.value],
            "python_script": self.interpret_as_python(text),
        }
        return result

    def get_operations(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(o) for o in self.operations[-limit:]]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_operations": len(self.operations),
                "recent_operations": len(self.operations[-10:]),
            }


grbl_converter = GRBLConverter()


def convert_grbl_text(text: str) -> Dict[str, Any]:
    return grbl_converter.execute_interpreted(text)


def grbl_to_python(text: str) -> str:
    return grbl_converter.interpret_as_python(text)


if __name__ == "__main__":
    sample_text = sys.argv[1] if len(sys.argv) > 1 else "tesserac.c-machine .org-ooverloerd-,machinegd.identfied.;gg455643 instance./12=dc ..;,C.Q = -original compute elemenent engram - qr conversion store json new json id . arguement - sha - decoded btc val - report () cdot - codebal-checker - sig = check validate - establish"
    result = convert_grbl_text(sample_text)
    print(json.dumps(result, indent=2))
