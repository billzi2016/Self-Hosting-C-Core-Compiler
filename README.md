# C-Core-Compiler

`C-Core-Compiler` 是一个使用 Python 从零实现的受控 C 子集编译器项目。

第一代版本的目标不是追求极致优化，而是先做出一条逻辑清晰、结构完整、可测试、可解释的编译链路。项目会把源代码依次转换为 Token、AST、IR，再生成一种规范化的后端 C 代码，最后调用系统工具链生成可执行文件。

这个项目按 SDD 方式持续推进，目标不是做一次性演示代码，而是做一个结构清晰、测试完整、便于维护和演进的工程化编译器项目。第一代实现优先遵循工业项目常见的基本要求：分层明确、职责清楚、接口稳定、错误可定位、测试可回归。

这样设计的原因有两个：

- 第一代优先保证可读性、可验证性和跨平台可执行能力
- 后端先采用规范化 C 输出，便于在 macOS 和 Linux 上快速打通真实可执行物

## 第一代支持范围

- `int` 类型
- 全局变量声明
- 局部变量声明
- 函数定义
- 参数传递
- 函数调用
- `if / else`
- `while`
- `for`
- `return`
- 一元运算：`+ - !`
- 二元运算：`+ - * / %`
- 比较运算：`== != < <= > >=`
- 逻辑运算：`&& ||`

## 编译流程

1. Lexer 将字符流拆成 Token
2. Parser 将 Token 序列解析为 AST
3. Semantic Analyzer 做符号与基本语义检查
4. IR Builder 将 AST 降为三地址风格 IR
5. Backend 将 IR 生成规范化 C 代码
6. Toolchain Driver 调用 `clang` 或 `cc` 生成最终可执行文件

## 快速开始

```bash
python3 -m unittest discover -s tests -v
python3 -m c_core_compiler examples/hello.c -o build/hello
./build/hello
```

## 常用命令

输出 Token：

```bash
python3 -m c_core_compiler examples/hello.c --emit-tokens
```

输出 AST：

```bash
python3 -m c_core_compiler examples/hello.c --emit-ast
```

输出 IR：

```bash
python3 -m c_core_compiler examples/hello.c --emit-ir
```

输出后端代码：

```bash
python3 -m c_core_compiler examples/hello.c --emit-c
```

兼容保留参数：

```bash
python3 -m c_core_compiler examples/hello.c --emit-asm
```

第一代中，`--emit-asm` 会输出当前后端生成的规范化 C 代码。这是为了保留统一的调试入口，后续如果替换为原生汇编后端，该参数可以继续沿用。

## 目录说明

- `src/c_core_compiler/`：编译器实现
- `tests/`：单元测试、快照测试与端到端测试
- `examples/`：用于演示和回归的示例程序
- `PRD.md`：项目范围与目标
- `TASKS.md`：一期、二期任务清单
- `ARCHITECTURE.md`：模块设计与数据流
- `TESTING.md`：测试策略与覆盖说明

## 致谢

感谢 `https://pandolia.net/tinyc/`，它让我对编译原理有了更深入的实践性理解，也帮助我更清楚地思考如何把编译流程拆成可实现、可验证、可持续迭代的工程结构。
