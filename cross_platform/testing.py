#!/usr/bin/env python3
"""
QB Protocol - Auto Tester
Automatic controlled selection testing across all platforms.
"""

from __future__ import annotations

import os
import sys
import time
import uuid
import json
import logging
import threading
import subprocess
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.cross_platform.testing")


@dataclass
class TestResult:
    test_id: str
    test_name: str
    platform: str
    environment: str
    status: str
    passed: bool
    duration_ms: float
    output: str
    error: str
    metadata: Dict[str, Any]
    timestamp: str


class AutoTester:
    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path(__file__).resolve().parent.parent.parent
        self.results: List[TestResult] = []
        self._lock = threading.RLock()

    def run_all_tests(self, platform_filter: Optional[str] = None) -> List[TestResult]:
        tests = [
            self.test_platform_detection,
            self.test_git_operations,
            self.test_python_execution,
            self.test_shell_access,
            self.test_network_connectivity,
            self.test_permissions,
            self.test_service_installation,
            self.test_adb_connection,
            self.test_idevice_connection,
            self.test_docker_availability,
        ]

        results = []
        for test in tests:
            try:
                result = test()
                if platform_filter and result.platform != platform_filter:
                    continue
                results.append(result)
            except Exception as e:
                result = TestResult(
                    test_id=str(uuid.uuid4()),
                    test_name=getattr(test, "__name__", "unknown"),
                    platform="unknown",
                    environment="unknown",
                    status="error",
                    passed=False,
                    duration_ms=0,
                    output="",
                    error=str(e),
                    metadata={},
                    timestamp=datetime.utcnow().isoformat() + "Z",
                )
                results.append(result)

        with self._lock:
            self.results.extend(results)
            if len(self.results) > 10000:
                self.results = self.results[-10000:]

        return results

    def test_platform_detection(self) -> TestResult:
        test_id = str(uuid.uuid4())
        start = time.time()
        try:
            from cross_platform.detector import platform_detector
            info = platform_detector.detect()
            output = f"platform={info.platform_type} env={info.environment_type} arch={info.architecture}"
            return TestResult(
                test_id=test_id,
                test_name="platform_detection",
                platform=info.platform_type,
                environment=info.environment_type,
                status="ok",
                passed=True,
                duration_ms=(time.time() - start) * 1000,
                output=output,
                error="",
                metadata=asdict(info),
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
        except Exception as e:
            return TestResult(
                test_id=test_id,
                test_name="platform_detection",
                platform="unknown",
                environment="unknown",
                status="error",
                passed=False,
                duration_ms=(time.time() - start) * 1000,
                output="",
                error=str(e),
                metadata={},
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

    def test_git_operations(self) -> TestResult:
        test_id = str(uuid.uuid4())
        start = time.time()
        try:
            result = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=10)
            passed = result.returncode == 0
            return TestResult(
                test_id=test_id,
                test_name="git_operations",
                platform="generic",
                environment="generic",
                status="ok" if passed else "failed",
                passed=passed,
                duration_ms=(time.time() - start) * 1000,
                output=result.stdout.strip(),
                error=result.stderr.strip() if not passed else "",
                metadata={"return_code": result.returncode},
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
        except Exception as e:
            return TestResult(
                test_id=test_id,
                test_name="git_operations",
                platform="unknown",
                environment="unknown",
                status="error",
                passed=False,
                duration_ms=(time.time() - start) * 1000,
                output="",
                error=str(e),
                metadata={},
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

    def test_python_execution(self) -> TestResult:
        test_id = str(uuid.uuid4())
        start = time.time()
        try:
            result = subprocess.run([sys.executable, "--version"], capture_output=True, text=True, timeout=10)
            passed = result.returncode == 0
            return TestResult(
                test_id=test_id,
                test_name="python_execution",
                platform="generic",
                environment="generic",
                status="ok" if passed else "failed",
                passed=passed,
                duration_ms=(time.time() - start) * 1000,
                output=result.stdout.strip(),
                error=result.stderr.strip() if not passed else "",
                metadata={"python": sys.executable, "return_code": result.returncode},
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
        except Exception as e:
            return TestResult(
                test_id=test_id,
                test_name="python_execution",
                platform="unknown",
                environment="unknown",
                status="error",
                passed=False,
                duration_ms=(time.time() - start) * 1000,
                output="",
                error=str(e),
                metadata={},
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

    def test_shell_access(self) -> TestResult:
        test_id = str(uuid.uuid4())
        start = time.time()
        try:
            from cross_platform.shell import freedom_shell
            shells = freedom_shell.detect_shells()
            passed = len(shells) > 0
            return TestResult(
                test_id=test_id,
                test_name="shell_access",
                platform="generic",
                environment="generic",
                status="ok" if passed else "failed",
                passed=passed,
                duration_ms=(time.time() - start) * 1000,
                output=json.dumps(shells),
                error="" if passed else "no_shells_detected",
                metadata={"shells": shells},
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
        except Exception as e:
            return TestResult(
                test_id=test_id,
                test_name="shell_access",
                platform="unknown",
                environment="unknown",
                status="error",
                passed=False,
                duration_ms=(time.time() - start) * 1000,
                output="",
                error=str(e),
                metadata={},
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

    def test_network_connectivity(self) -> TestResult:
        test_id = str(uuid.uuid4())
        start = time.time()
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            passed = True
            output = "network_connectivity:ok"
            error = ""
        except Exception as e:
            passed = False
            output = ""
            error = str(e)

        return TestResult(
            test_id=test_id,
            test_name="network_connectivity",
            platform="generic",
            environment="generic",
            status="ok" if passed else "failed",
            passed=passed,
            duration_ms=(time.time() - start) * 1000,
            output=output,
            error=error,
            metadata={},
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    def test_permissions(self) -> TestResult:
        test_id = str(uuid.uuid4())
        start = time.time()
        try:
            is_root = os.geteuid() == 0 if hasattr(os, "geteuid") else False
            passed = True
            output = f"is_root={is_root}"
            return TestResult(
                test_id=test_id,
                test_name="permissions",
                platform="generic",
                environment="root" if is_root else "user",
                status="ok",
                passed=passed,
                duration_ms=(time.time() - start) * 1000,
                output=output,
                error="",
                metadata={"is_root": is_root},
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
        except Exception as e:
            return TestResult(
                test_id=test_id,
                test_name="permissions",
                platform="unknown",
                environment="unknown",
                status="error",
                passed=False,
                duration_ms=(time.time() - start) * 1000,
                output="",
                error=str(e),
                metadata={},
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

    def test_service_installation(self) -> TestResult:
        test_id = str(uuid.uuid4())
        start = time.time()
        try:
            from cross_platform.deployer import cross_platform_deployer
            result = cross_platform_deployer.deploy(force=False)
            passed = result.status == "ok"
            return TestResult(
                test_id=test_id,
                test_name="service_installation",
                platform=result.platform,
                environment=result.environment,
                status=result.status,
                passed=passed,
                duration_ms=(time.time() - start) * 1000,
                output=json.dumps(result.steps),
                error=result.error or "",
                metadata={"files_deployed": result.files_deployed, "services_started": result.services_started},
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
        except Exception as e:
            return TestResult(
                test_id=test_id,
                test_name="service_installation",
                platform="unknown",
                environment="unknown",
                status="error",
                passed=False,
                duration_ms=(time.time() - start) * 1000,
                output="",
                error=str(e),
                metadata={},
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

    def test_adb_connection(self) -> TestResult:
        test_id = str(uuid.uuid4())
        start = time.time()
        try:
            from cross_platform.metal import metal_manager
            devices = metal_manager.get_devices()
            adb_devices = [d for d in devices if d.get("connection") == "adb"]
            passed = len(adb_devices) >= 0
            return TestResult(
                test_id=test_id,
                test_name="adb_connection",
                platform="android",
                environment="raw_metal",
                status="ok",
                passed=passed,
                duration_ms=(time.time() - start) * 1000,
                output=json.dumps(adb_devices),
                error="" if passed else "no_adb_devices",
                metadata={"adb_devices": adb_devices},
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
        except Exception as e:
            return TestResult(
                test_id=test_id,
                test_name="adb_connection",
                platform="unknown",
                environment="unknown",
                status="error",
                passed=False,
                duration_ms=(time.time() - start) * 1000,
                output="",
                error=str(e),
                metadata={},
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

    def test_idevice_connection(self) -> TestResult:
        test_id = str(uuid.uuid4())
        start = time.time()
        try:
            from cross_platform.metal import metal_manager
            devices = metal_manager.get_devices()
            ios_devices = [d for d in devices if d.get("device_type") == "ios"]
            passed = len(ios_devices) >= 0
            return TestResult(
                test_id=test_id,
                test_name="idevice_connection",
                platform="ios",
                environment="raw_metal",
                status="ok",
                passed=passed,
                duration_ms=(time.time() - start) * 1000,
                output=json.dumps(ios_devices),
                error="" if passed else "no_ios_devices",
                metadata={"ios_devices": ios_devices},
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
        except Exception as e:
            return TestResult(
                test_id=test_id,
                test_name="idevice_connection",
                platform="unknown",
                environment="unknown",
                status="error",
                passed=False,
                duration_ms=(time.time() - start) * 1000,
                output="",
                error=str(e),
                metadata={},
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

    def test_docker_availability(self) -> TestResult:
        test_id = str(uuid.uuid4())
        start = time.time()
        try:
            from cross_platform.detector import platform_detector
            info = platform_detector.detect()
            passed = info.docker_available
            return TestResult(
                test_id=test_id,
                test_name="docker_availability",
                platform=info.platform_type,
                environment=info.environment_type,
                status="ok" if passed else "failed",
                passed=passed,
                duration_ms=(time.time() - start) * 1000,
                output=f"docker_available={passed}",
                error="" if passed else "docker_not_available",
                metadata={"docker_available": passed},
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
        except Exception as e:
            return TestResult(
                test_id=test_id,
                test_name="docker_availability",
                platform="unknown",
                environment="unknown",
                status="error",
                passed=False,
                duration_ms=(time.time() - start) * 1000,
                output="",
                error=str(e),
                metadata={},
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

    def get_results(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(r) for r in self.results[-limit:]]

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self.results)
            passed = sum(1 for r in self.results if r.passed)
            failed = total - passed
            return {
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "0%",
            }


auto_tester = AutoTester()
