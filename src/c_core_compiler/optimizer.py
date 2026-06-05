"""模块说明：提供一个清晰的优化管线入口。

第一代编译器刻意不把重点放在激进优化上。
这个模块先把优化阶段的接口稳定下来，后续再在不破坏整体结构的前提下，
加入少量、可解释、可测试的优化规则。
"""

from __future__ import annotations

from dataclasses import dataclass

from .ir import IRProgram


@dataclass(slots=True)
class Optimizer:
    program: IRProgram

    def run(self) -> IRProgram:
        """第一代基线版本暂时不改写 IR，直接原样返回。"""

        return self.program
