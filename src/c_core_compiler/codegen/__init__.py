"""模块说明：根据目标平台选择后端实现。"""

from __future__ import annotations

from .linux_x86_64 import LinuxBackend
from .macos_x86_64 import MacOSBackend


def get_backend(target: str):
    if target == "linux-x86_64":
        return LinuxBackend()
    if target == "macos-x86_64":
        return MacOSBackend()
    raise ValueError(f"unsupported target: {target}")
