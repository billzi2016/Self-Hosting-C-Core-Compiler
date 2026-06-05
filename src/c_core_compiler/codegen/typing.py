"""模块说明：共享少量后端元数据，避免在后端之间重复硬编码。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BackendMeta:
    target_name: str
