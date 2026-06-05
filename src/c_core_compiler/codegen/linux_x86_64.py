"""模块说明：提供 Linux 目标下的第一代后端外观。"""

from __future__ import annotations

from ._portable_c import emit_portable_c
from .typing import BackendMeta
from ..ir import IRProgram


class LinuxBackend:
    def emit(self, program: IRProgram) -> str:
        return emit_portable_c(program, BackendMeta("linux-x86_64"))
