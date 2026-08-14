#!/usr/bin/env python3
"""
QB Protocol - Cross-Platform API Routes
Auto-deployment, freedom shell, metal access, cloud conversion, testing.
"""

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse, RedirectResponse
from typing import Dict, Any, Optional
from dataclasses import asdict

try:
    from qb_protocol.cross_platform.detector import platform_detector
    from qb_protocol.cross_platform.deployer import cross_platform_deployer
    from qb_protocol.cross_platform.shell import freedom_shell
    from qb_protocol.cross_platform.metal import metal_manager
    from qb_protocol.cross_platform.cloud import cloud_converter
    from qb_protocol.cross_platform.testing import auto_tester
    HAS_CROSS_PLATFORM = True
except ImportError:
    try:
        from cross_platform.detector import platform_detector
        from cross_platform.deployer import cross_platform_deployer
        from cross_platform.shell import freedom_shell
        from cross_platform.metal import metal_manager
        from cross_platform.cloud import cloud_converter
        from cross_platform.testing import auto_tester
        HAS_CROSS_PLATFORM = True
    except ImportError:
        HAS_CROSS_PLATFORM = False

router = APIRouter(prefix="/cross-platform", tags=["cross-platform"])


@router.get("/status")
def cross_platform_status():
    if not HAS_CROSS_PLATFORM:
        return {"error": "cross_platform_unavailable"}
    return platform_detector.get_status()


@router.post("/detect")
def detect_platform():
    if not HAS_CROSS_PLATFORM:
        return {"error": "cross_platform_unavailable"}
    info = platform_detector.detect(force=True)
    return asdict(info)


@router.post("/deploy")
def deploy_cross_platform(body: Dict[str, Any] = Body(...)):
    if not HAS_CROSS_PLATFORM:
        return {"error": "cross_platform_unavailable"}
    target = body.get("target")
    force = body.get("force", False)
    result = cross_platform_deployer.deploy(target=target, force=force)
    return asdict(result)


@router.get("/deploy/history")
def deploy_history(limit: int = 50):
    if not HAS_CROSS_PLATFORM:
        return {"error": "cross_platform_unavailable"}
    return {"history": cross_platform_deployer.get_history(limit=limit)}


@router.get("/shell/status")
def shell_status():
    if not HAS_CROSS_PLATFORM:
        return {"error": "cross_platform_unavailable"}
    return freedom_shell.get_status()


@router.post("/shell/execute")
def shell_execute(body: Dict[str, Any] = Body(...)):
    if not HAS_CROSS_PLATFORM:
        return {"error": "cross_platform_unavailable"}
    command = body.get("command", "")
    args = body.get("args", [])
    cwd = body.get("cwd")
    env = body.get("env")
    timeout = float(body.get("timeout", 30.0))
    shell = body.get("shell")
    admin = body.get("admin", False)
    raw_metal = body.get("raw_metal", False)
    if not command:
        return {"error": "command_required"}
    if raw_metal:
        result = freedom_shell.execute_raw_metal(command, args=args, cwd=cwd, env=env, timeout=timeout)
    elif admin:
        result = freedom_shell.execute_admin(command, args=args, cwd=cwd, env=env, timeout=timeout)
    else:
        result = freedom_shell.execute(command, args=args, cwd=cwd, env=env, timeout=timeout, shell=shell)
    return asdict(result)


@router.get("/shell/history")
def shell_history(limit: int = 100):
    if not HAS_CROSS_PLATFORM:
        return {"error": "cross_platform_unavailable"}
    return {"history": freedom_shell.get_history(limit=limit)}


@router.post("/shell/chain")
def shell_chain(body: Dict[str, Any] = Body(...)):
    if not HAS_CROSS_PLATFORM:
        return {"error": "cross_platform_unavailable"}
    commands = body.get("commands", [])
    shell = body.get("shell")
    timeout = float(body.get("timeout", 60.0))
    if not commands:
        return {"error": "commands_required"}
    results = freedom_shell.execute_chained(commands, shell=shell, timeout=timeout)
    return {"results": [asdict(r) for r in results]}


@router.post("/shell/pipe")
def shell_pipe(body: Dict[str, Any] = Body(...)):
    if not HAS_CROSS_PLATFORM:
        return {"error": "cross_platform_unavailable"}
    pipeline = body.get("pipeline", "")
    shell = body.get("shell")
    timeout = float(body.get("timeout", 60.0))
    if not pipeline:
        return {"error": "pipeline_required"}
    result = freedom_shell.execute_piped(pipeline, shell=shell, timeout=timeout)
    return asdict(result)


@router.get("/shell/plugins")
def shell_plugins():
    if not HAS_CROSS_PLATFORM:
        return {"error": "cross_platform_unavailable"}
    return {"plugins": freedom_shell.get_plugins()}


@router.post("/shell/translate")
def shell_translate(body: Dict[str, Any] = Body(...)):
    if not HAS_CROSS_PLATFORM:
        return {"error": "cross_platform_unavailable"}
    command = body.get("command", "")
    target_shell = body.get("target_shell", "bash")
    if not command:
        return {"error": "command_required"}
    translated = freedom_shell._build_command(target_shell, command, None)
    return {"original": command, "translated": " ".join(translated), "shell": target_shell}


@router.get("/shell/cmd/support")
def cmd_support():
    if not HAS_CROSS_PLATFORM:
        return {"error": "cross_platform_unavailable"}
    return {
        "cmd_available": shutil.which("cmd.exe") or shutil.which("cmd"),
        "cmd_modes": ["/c", "/k", "/q", "/a"],
        "windows_commands": [
            "dir", "copy", "move", "del", "cls", "type", "find", "findstr",
            "sort", "more", "fc", "tree", "ipconfig", "ping", "tracert",
            "netstat", "tasklist", "taskkill", "wmic", "powershell", "cmd"
        ],
        "cross_platform_equivalents": {
            "dir": "ls",
            "copy": "cp",
            "move": "mv",
            "del": "rm",
            "cls": "clear",
            "type": "cat",
            "find": "grep",
            "findstr": "grep",
            "sort": "sort",
            "more": "less",
            "fc": "diff",
            "tree": "tree",
            "ipconfig": "ifconfig",
            "ping": "ping",
            "tracert": "traceroute",
            "netstat": "netstat",
            "tasklist": "ps aux",
            "taskkill": "kill",
            "wmic": "systeminfo",
            "powershell": "pwsh",
            "cmd": "bash",
        }
    }


@router.get("/metal/devices")
def metal_devices():
    if not HAS_CROSS_PLATFORM:
        return {"error": "cross_platform_unavailable"}
    return metal_manager.get_devices()


@router.post("/metal/devices/refresh")
def metal_refresh():
    if not HAS_CROSS_PLATFORM:
        return {"error": "cross_platform_unavailable"}
    return metal_manager.refresh_devices()


@router.post("/metal/execute")
def metal_execute(body: Dict[str, Any] = Body(...)):
    if not HAS_CROSS_PLATFORM:
        return {"error": "cross_platform_unavailable"}
    command = body.get("command", "")
    args = body.get("args", [])
    device_id = body.get("device_id")
    connection = body.get("connection")
    cwd = body.get("cwd")
    env = body.get("env")
    timeout = float(body.get("timeout", 60.0))
    if not command:
        return {"error": "command_required"}
    result = metal_manager.execute(command, args=args, cwd=cwd, env=env, timeout=timeout, device_id=device_id, connection=connection)
    return result


@router.get("/metal/device/{device_id}")
def metal_device(device_id: str):
    if not HAS_CROSS_PLATFORM:
        return {"error": "cross_platform_unavailable"}
    device = metal_manager.get_device(device_id)
    if not device:
        return {"error": "device_not_found"}
    return device


@router.post("/cloud/convert")
def cloud_convert(body: Dict[str, Any] = Body(...)):
    if not HAS_CROSS_PLATFORM:
        return {"error": "cross_platform_unavailable"}
    instance_id = body.get("instance_id", "")
    target_os = body.get("target_os", "ubuntu")
    if not instance_id:
        return {"error": "instance_id_required"}
    return cloud_converter.convert_to_metal(instance_id=instance_id, target_os=target_os)


@router.post("/cloud/provision")
def cloud_provision(body: Dict[str, Any] = Body(...)):
    if not HAS_CROSS_PLATFORM:
        return {"error": "cross_platform_unavailable"}
    provider = body.get("provider", "aws")
    region = body.get("region", "us-east-1")
    os_image = body.get("os_image", "ubuntu-22.04")
    instance_type = body.get("instance_type", "t2.micro")
    return cloud_converter.provision_instance(provider=provider, region=region, os_image=os_image, instance_type=instance_type)


@router.get("/cloud/instances")
def cloud_instances():
    if not HAS_CROSS_PLATFORM:
        return {"error": "cross_platform_unavailable"}
    return cloud_converter.get_instances()


@router.get("/cloud/instance/{instance_id}")
def cloud_instance(instance_id: str):
    if not HAS_CROSS_PLATFORM:
        return {"error": "cross_platform_unavailable"}
    instance = cloud_converter.get_instance(instance_id)
    if not instance:
        return {"error": "instance_not_found"}
    return instance


@router.post("/testing/run")
def run_tests(body: Dict[str, Any] = Body(...)):
    if not HAS_CROSS_PLATFORM:
        return {"error": "cross_platform_unavailable"}
    platform_filter = body.get("platform_filter")
    results = auto_tester.run_all_tests(platform_filter=platform_filter)
    return {"results": [asdict(r) for r in results], "summary": auto_tester.get_summary()}


@router.get("/testing/results")
def test_results(limit: int = 100):
    if not HAS_CROSS_PLATFORM:
        return {"error": "cross_platform_unavailable"}
    return {"results": auto_tester.get_results(limit=limit), "summary": auto_tester.get_summary()}


@router.get("/testing/summary")
def test_summary():
    if not HAS_CROSS_PLATFORM:
        return {"error": "cross_platform_unavailable"}
    return auto_tester.get_summary()


@router.get("/")
def cross_platform_root():
    return RedirectResponse(url="/cross-platform/status")
