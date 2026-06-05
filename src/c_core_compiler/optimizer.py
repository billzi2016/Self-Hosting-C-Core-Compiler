"""模块说明：提供一个清晰、保守、可验证的优化管线。

这个优化器不追求复杂算法，而是优先做三件容易解释且足够安全的事情：

1. 只在临时变量层面做常量传播；
2. 只折叠确定无歧义的一元/二元常量表达式；
3. 在分支被简化后，删除明显不可达的 IR 指令。

这样做的目的是在不牺牲整体可读性的前提下，让第二阶段相较第一代基线
确实有“优化已经开始发挥作用”的可见提升。
"""

from __future__ import annotations

from dataclasses import dataclass

from .ir import IRFunction, IRInstruction, IRProgram
from .semantic import _evaluate_binary


@dataclass(slots=True)
class Optimizer:
    program: IRProgram

    def run(self) -> IRProgram:
        """按固定顺序执行一组保守优化。"""

        optimized_functions = [self._optimize_function(function) for function in self.program.functions]
        return IRProgram(globals=self.program.globals, functions=optimized_functions)

    def _optimize_function(self, function: IRFunction) -> IRFunction:
        folded = self._fold_constants(function)
        reachable = self._prune_unreachable(folded)
        return reachable

    def _fold_constants(self, function: IRFunction) -> IRFunction:
        """在函数内部做保守常量传播和常量折叠。

        这里故意只跟踪临时变量，因为临时变量在 IRBuilder 里是单次赋值生成的，
        不会像局部变量那样被多次写入，因而传播规则更稳定、更容易验证。
        """

        constants: dict[str, int] = {}
        instructions: list[IRInstruction] = []

        for instruction in function.instructions:
            op = instruction.opcode
            args = instruction.args

            if op == "const":
                target = args[0]
                value = int(args[1])
                constants[target] = value
                instructions.append(instruction)
                continue

            if op == "copy":
                target, source = args
                if source in constants:
                    value = constants[source]
                    constants[target] = value
                    instructions.append(IRInstruction("const", (target, str(value))))
                else:
                    constants.pop(target, None)
                    instructions.append(instruction)
                continue

            if op == "unary":
                target, operator, operand = args
                if operand in constants:
                    value = _eval_unary(operator, constants[operand])
                    constants[target] = value
                    instructions.append(IRInstruction("const", (target, str(value))))
                else:
                    constants.pop(target, None)
                    instructions.append(instruction)
                continue

            if op == "binary":
                target, operator, left, right = args
                if left in constants and right in constants:
                    value = _evaluate_binary(operator, constants[left], constants[right])
                    constants[target] = value
                    instructions.append(IRInstruction("const", (target, str(value))))
                else:
                    constants.pop(target, None)
                    instructions.append(instruction)
                continue

            if op == "cjump":
                condition, true_label, false_label = args
                if condition in constants:
                    chosen = true_label if constants[condition] != 0 else false_label
                    instructions.append(IRInstruction("jump", (chosen,)))
                else:
                    instructions.append(instruction)
                continue

            if op == "call":
                target = args[0]
                constants.pop(target, None)
                instructions.append(instruction)
                continue

            if op == "load":
                target = args[0]
                constants.pop(target, None)
                instructions.append(instruction)
                continue

            # store / jump / label / return 等指令不引入新的可折叠临时值，
            # 直接保留即可。
            instructions.append(instruction)

        return IRFunction(
            name=function.name,
            params=function.params,
            locals=function.locals,
            temporaries=function.temporaries,
            instructions=instructions,
        )

    def _prune_unreachable(self, function: IRFunction) -> IRFunction:
        """基于显式控制流做一次可达性裁剪。"""

        instructions = function.instructions
        if not instructions:
            return function

        label_to_index = {
            instruction.args[0]: index
            for index, instruction in enumerate(instructions)
            if instruction.opcode == "label"
        }

        worklist = [0]
        reachable: set[int] = set()

        while worklist:
            index = worklist.pop()
            if index in reachable or index < 0 or index >= len(instructions):
                continue
            reachable.add(index)

            instruction = instructions[index]
            op = instruction.opcode

            if op == "return":
                continue
            if op == "jump":
                target = label_to_index[instruction.args[0]]
                worklist.append(target)
                continue
            if op == "cjump":
                worklist.append(label_to_index[instruction.args[1]])
                worklist.append(label_to_index[instruction.args[2]])
                continue

            worklist.append(index + 1)

        pruned = [instruction for index, instruction in enumerate(instructions) if index in reachable]
        return IRFunction(
            name=function.name,
            params=function.params,
            locals=function.locals,
            temporaries=function.temporaries,
            instructions=pruned,
        )


def _eval_unary(operator: str, operand: int) -> int:
    if operator == "+":
        return operand
    if operator == "-":
        return -operand
    if operator == "!":
        return int(not operand)
    raise AssertionError(f"unsupported unary operator: {operator}")
