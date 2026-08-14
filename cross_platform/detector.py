#!/usr/bin/env python3
"""
QB Protocol - Platform Detector
Auto-detects all supported platforms and environments.
"""

from __future__ import annotations

import os
import sys
import time
import uuid
import json
import logging
import platform
import subprocess
import re
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

LOG = logging.getLogger("qb_protocol.cross_platform.detector")


class PlatformType(Enum):
    WINDOWS = "windows"
    WSL = "wsl"
    LINUX_ARCH = "linux_arch"
    LINUX_UBUNTU = "linux_ubuntu"
    LINUX_DEBIAN = "linux_debian"
    LINUX_GENERIC = "linux_generic"
    MACOS_INTEL = "macos_intel"
    MACOS_APPLE_SILICON = "macos_apple_silicon"
    ANDROID = "android"
    IOS = "ios"
    UNKNOWN = "unknown"


class EnvironmentType(Enum):
    ROOT = "root"
    ADMIN = "admin"
    USER = "user"
    RAW_METAL = "raw_metal"
    CLOUD = "cloud"
    CONTAINER = "container"
    VM = "vm"


@dataclass
class PlatformInfo:
    platform_type: str
    environment_type: str
    os_name: str
    os_version: str
    architecture: str
    hostname: str
    is_admin: bool
    is_root: bool
    shell: str
    python_version: str
    node_version: Optional[str]
    docker_available: bool
    adb_available: bool
    idevice_available: bool
    metadata: Dict[str, Any]
    detected_at: str


class PlatformDetector:
    def __init__(self):
        self.detection_cache: Optional[PlatformInfo] = None
        self.detection_time: Optional[float] = None

    def detect(self, force: bool = False) -> PlatformInfo:
        if not force and self.detection_cache and (time.time() - self.detection_time) < 300:
            return self.detection_cache

        platform_type = self._detect_platform_type()
        environment_type = self._detect_environment_type()
        os_name, os_version = self._detect_os()
        architecture = self._detect_architecture()
        hostname = self._detect_hostname()
        is_admin, is_root = self._detect_privileges()
        shell = self._detect_shell()
        python_version = self._detect_python_version()
        node_version = self._detect_node_version()
        docker_available = self._check_docker()
        adb_available = self._check_adb()
        idevice_available = self._check_idevice()

        metadata = {
            "platform_machine": platform.machine(),
            "platform_processor": platform.processor(),
            "system": platform.system(),
            "release": platform.release(),
            "wsl_distro": self._detect_wsl_distro(),
            "android_build": self._detect_android_build(),
            "ios_model": self._detect_ios_model(),
        }

        self.detection_cache = PlatformInfo(
            platform_type=platform_type.value,
            environment_type=environment_type.value,
            os_name=os_name,
            os_version=os_version,
            architecture=architecture,
            hostname=hostname,
            is_admin=is_admin,
            is_root=is_root,
            shell=shell,
            python_version=python_version,
            node_version=node_version,
            docker_available=docker_available,
            adb_available=adb_available,
            idevice_available=idevice_available,
            metadata=metadata,
            detected_at=datetime.utcnow().isoformat() + "Z",
        )
        self.detection_time = time.time()
        return self.detection_cache

    def _detect_platform_type(self) -> PlatformType:
        if sys.platform == "darwin":
            machine = platform.machine().lower()
            if machine in ("arm64", "aarch64"):
                return PlatformType.MACOS_APPLE_SILICON
            return PlatformType.MACOS_INTEL

        if sys.platform == "win32":
            return PlatformType.WINDOWS

        if sys.platform.startswith("linux"):
            if self._is_wsl():
                return PlatformType.WSL
            if self._is_android():
                return PlatformType.ANDROID
            if self._is_arch():
                return PlatformType.LINUX_ARCH
            if self._is_ubuntu():
                return PlatformType.LINUX_UBUNTU
            if self._is_debian():
                return PlatformType.LINUX_DEBIAN
            return PlatformType.LINUX_GENERIC

        return PlatformType.UNKNOWN

    def _detect_environment_type(self) -> EnvironmentType:
        if os.geteuid() == 0 if hasattr(os, "geteuid") else False:
            return EnvironmentType.ROOT
        if self._is_admin():
            return EnvironmentType.ADMIN
        if self._is_raw_metal():
            return EnvironmentType.RAW_METAL
        if self._is_cloud():
            return EnvironmentType.CLOUD
        if self._is_container():
            return EnvironmentType.CONTAINER
        if self._is_vm():
            return EnvironmentType.VM
        return EnvironmentType.USER

    def _detect_os(self) -> tuple[str, str]:
        if sys.platform == "darwin":
            return "macOS", platform.mac_ver()[0]
        if sys.platform == "win32":
            return "Windows", platform.win32_ver()[0]
        if sys.platform.startswith("linux"):
            try:
                with open("/etc/os-release") as f:
                    content = f.read()
                name_match = re.search(r'ID=(?:"([^"]+)"|([^"\n]+))', content)
                version_match = re.search(r'VERSION_ID=(?:"([^"]+)"|([^"\n]+))', content)
                name = name_match.group(1) or name_match.group(2) if name_match else "Linux"
                version = version_match.group(1) or version_match.group(2) if version_match else "unknown"
                return name, version
            except Exception:
                pass
            return "Linux", platform.release()
        return "Unknown", "unknown"

    def _detect_architecture(self) -> str:
        machine = platform.machine().lower()
        if machine in ("x86_64", "amd64"):
            return "x86_64"
        if machine in ("arm64", "aarch64"):
            return "arm64"
        if machine in ("i386", "i686"):
            return "x86"
        return machine

    def _detect_hostname(self) -> str:
        try:
            return platform.node()
        except Exception:
            return "unknown"

    def _detect_privileges(self) -> tuple[bool, bool]:
        is_root = False
        is_admin = False

        if hasattr(os, "geteuid"):
            is_root = os.geteuid() == 0
        if hasattr(os, "getuid"):
            is_root = is_root or os.getuid() == 0

        if sys.platform == "win32":
            try:
                import ctypes
                is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            except Exception:
                pass

        return is_admin, is_root

    def _detect_shell(self) -> str:
        return os.environ.get("SHELL", os.environ.get("COMSPEC", "unknown"))

    def _detect_python_version(self) -> str:
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    def _detect_node_version(self) -> Optional[str]:
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def _check_docker(self) -> bool:
        try:
            subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=5, check=True)
            return True
        except Exception:
            return False

    def _check_adb(self) -> bool:
        try:
            subprocess.run(["adb", "version"], capture_output=True, text=True, timeout=5, check=True)
            return True
        except Exception:
            return False

    def _check_idevice(self) -> bool:
        try:
            subprocess.run(["ideviceinfo", "--version"], capture_output=True, text=True, timeout=5, check=True)
            return True
        except Exception:
            return False

    def _is_wsl(self) -> bool:
        try:
            with open("/proc/version") as f:
                content = f.read().lower()
            return "microsoft" in content or "wsl" in content
        except Exception:
            return False

    def _is_android(self) -> bool:
        return os.path.exists("/system/build.prop")

    def _is_arch(self) -> bool:
        return os.path.exists("/etc/arch-release")

    def _is_ubuntu(self) -> bool:
        return os.path.exists("/etc/lsb-release") and "ubuntu" in open("/etc/lsb-release").read().lower()

    def _is_debian(self) -> bool:
        return os.path.exists("/etc/debian_version")

    def _detect_wsl_distro(self) -> Optional[str]:
        if not self._is_wsl():
            return None
        try:
            result = subprocess.run(["cat", "/etc/os-release"], capture_output=True, text=True, timeout=5)
            for line in result.stdout.splitlines():
                if line.startswith("NAME="):
                    return line.split("=", 1)[1].strip('"')
        except Exception:
            pass
        return "WSL"

    def _detect_android_build(self) -> Optional[str]:
        if not self._is_android():
            return None
        try:
            with open("/system/build.prop") as f:
                for line in f:
                    if line.startswith("ro.build.display.id="):
                        return line.split("=", 1)[1].strip()
        except Exception:
            pass
        return "Android"

    def _detect_ios_model(self) -> Optional[str]:
        return None

    def _is_admin(self) -> bool:
        if sys.platform == "win32":
            try:
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            except Exception:
                return False
        if hasattr(os, "getuid"):
            return os.getuid() == 0
        return False

    def _is_raw_metal(self) -> bool:
        return not self._is_container() and not self._is_vm() and not self._is_cloud()

    def _is_cloud(self) -> bool:
        cloud_indicators = [
            "/sys/class/dmi/id/product_uuid",
            "/sys/class/dmi/id/board_vendor",
            "/sys/class/dmi/id/bios_vendor",
            "/sys/class/dmi/id/chassis_vendor",
        ]
        if not all(os.path.exists(p) for p in cloud_indicators):
            return True
        try:
            for path in cloud_indicators:
                with open(path) as f:
                    content = f.read().lower()
                    if any(vendor in content for vendor in ["amazon", "google", "microsoft", "azure", "qemu", "kvm", "vmware", "xen", "oracle", "parallels"]):
                        return True
        except Exception:
            pass
        return False

    def _is_container(self) -> bool:
        return os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv")

    def _is_vm(self) -> bool:
        try:
            with open("/sys/class/dmi/id/product_name") as f:
                product = f.read().lower()
            vm_indicators = ["vmware", "virtualbox", "qemu", "kvm", "hyper-v", "parallels", "xen"]
            return any(indicator in product for indicator in vm_indicators)
        except Exception:
            return False

    def get_status(self) -> Dict[str, Any]:
        info = self.detect()
        return asdict(info)


platform_detector = PlatformDetector()
