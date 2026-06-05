# 自举重构 PRD：用 C 语言重写编译器并实现自举

## 目标

将现有 Python 实现的 C 子集编译器，改写为用 C 语言编写的版本，最终实现**自举（self-hosting）**：即用这个 C 编译器本身来编译自己的源代码，输出功能等价的可执行文件。

---

## 背景

当前状态：

- 编译器用 Python 编写，分为 Lexer → Parser → Semantic → IR Builder → IR Optimizer → Codegen（输出规范化 C）→ 调用系统 clang 生成可执行文件
- 支持语言特性：`int`/`char` 类型、指针、定长数组、`if`/`else`/`while`/`for`/`return`、字符串/字符字面量、算术/比较/逻辑运算符、函数定义与调用、全局变量

自举的意义：

- 证明编译器实现了足够完整的 C 子集，能够表达自身逻辑
- 摆脱对 Python 运行时的依赖，编译器本身成为独立的本地二进制
- 符合项目名称 `Self-Hosting-C-Core-Compiler` 的最终目标

---

## 自举三阶段模型

```
Gen 0 (g0): Python 编译器（现有）
    ↓ 编译 compiler.c
Gen 1 (g1): 第一代 C 编译器二进制
    ↓ 编译 compiler.c
Gen 2 (g2): 第二代 C 编译器二进制
    ↓ 验证：g1 与 g2 的输出功能等价
    → 自举成立 ✓
```

---

## 阶段一：扩展 Python 编译器支持的语言特性

为了能够用 C 写编译器，Python 编译器需要先支持以下额外的 C 语法（写编译器本身会用到）：

### 1.1 类型系统扩展

| 特性 | 说明 | 优先级 |
|------|------|--------|
| `void` 返回类型 | 过程函数不返回值 | P0 |
| `void *` 泛型指针 | malloc 返回值等 | P0 |
| `struct` 定义与访问 | AST 节点等结构体 | P0 |
| `typedef struct` | 简化结构体类型名 | P0 |
| `unsigned int` / `size_t` | 长度与计数场景 | P1 |

### 1.2 表达式与语句扩展

| 特性 | 说明 | 优先级 |
|------|------|--------|
| 后缀 `++` / `--` | 循环计数器 | P0 |
| 前缀 `++` / `--` | 同上 | P0 |
| `break` / `continue` | 循环控制 | P0 |
| 强制类型转换 `(T)expr` | malloc 结果转换 | P0 |
| 十六进制整数字面量 `0x...` | 位操作、token kind | P0 |
| 三目运算符 `a ? b : c` | 简化条件赋值 | P1 |
| 结构体成员访问 `.` 和 `->` | 访问 AST 字段 | P0 |
| `sizeof(T)` | malloc 大小计算 | P0 |
| 多变量声明 `int a, b;` | 可选，不强制 | P2 |

### 1.3 语义检查放宽

| 特性 | 说明 | 优先级 |
|------|------|--------|
| 允许调用未在源码中定义的外部函数 | `malloc`, `fopen`, `strcmp` 等标准库 | P0 |
| `void` 函数不强制 `return` | 过程函数 | P0 |
| 允许 `return;`（无值返回）| void 函数 | P0 |

### 1.4 代码生成扩展

| 特性 | 说明 |
|------|------|
| 生成的 C 头部增加 `#include <stdlib.h>` `#include <string.h>` | 支持标准库调用 |
| struct 定义输出 | 在函数前输出结构体声明 |
| `->` 成员访问生成 | |

---

## 阶段二：用 C 写编译器源代码（bootstrap/compiler.c）

### 2.1 设计原则

- 只使用阶段一完成后 Python 编译器支持的 C 子集
- 用 `struct` 表示 Token、AST 节点、IR 指令
- 用基于 `malloc` 的简单 arena 分配器管理内存（无需 GC）
- 输出目标：规范化 C 代码（与 Python 编译器一致，再调用 clang）

### 2.2 模块划分（单文件或多文件）

```
bootstrap/
  compiler.c      主编译器源码（或拆分为多个 .c 文件）
  bootstrap.sh    自举验证脚本
  Makefile        构建入口
```

### 2.3 compiler.c 内部模块

```
全局常量 / 枚举
  TokenKind 枚举（整数常量）

结构体定义
  Token    { kind, value[256], line, col }
  Node     { kind, type_base, type_ptr_level, ... children }
  IRInstr  { opcode, args[4][64] }
  IRFunc   { name, params[], locals[], instrs[] }

词法分析（Lexer）
  tokenize(source) -> Token[]

语法分析（Parser）
  parse_program(tokens) -> Node*

语义检查（Semantic）
  analyze(program)

IR 构建（IRBuilder）
  build_ir(program) -> IRFunc[]

代码生成（Codegen）
  emit_c(funcs) -> void  // 输出到 stdout 或文件

主函数（main）
  读取文件 -> 调用各阶段 -> 输出生成 C -> 调用 clang
```

### 2.4 内存策略

采用简单线性 arena：
```c
char mem[4 * 1024 * 1024];  /* 4MB 静态 arena */
int  mem_top = 0;

void *arena_alloc(int size) {
    void *p = mem + mem_top;
    mem_top = mem_top + size;
    return p;
}
```
或使用 `malloc`（通过 `stdlib.h` 调用）。

---

## 阶段三：自举验证

### 3.1 bootstrap.sh 流程

```bash
#!/bin/bash
set -e

# Step 1: g0 (Python) 编译 compiler.c → g1
python -m c_core_compiler bootstrap/compiler.c -o build/compiler_g1

# Step 2: g1 编译 compiler.c → g2
./build/compiler_g1 bootstrap/compiler.c -o build/compiler_g2

# Step 3: g2 编译 compiler.c → g3
./build/compiler_g2 bootstrap/compiler.c -o build/compiler_g3

# Step 4: 验证 g2 与 g3 的输出二进制等价（自举稳定性）
diff build/compiler_g2 build/compiler_g3 && echo "✓ 自举成立" || echo "✗ 自举失败"
```

注：g1 和 g2 之间二进制未必完全相同（因为 clang 优化），
但 g2 和 g3 必须完全相同，说明自举已稳定。

---

## 阶段四：回归测试

- 现有 Python 编译器的 examples/ 全部测试用例，必须在 C 编译器上通过
- 增加交叉验证：Python 编译器 vs C 编译器对同一输入的输出结果相同

---

## 里程碑时间线

| 里程碑 | 内容 | 状态 |
|--------|------|------|
| M0 | 整理现有代码，移动旧文档，写本 PRD | ✅ 完成 |
| M1 | 扩展 Python 编译器：void、struct、typedef、++/--、break/continue、cast、extern call | 待开始 |
| M2 | 扩展代码生成：输出 struct 定义、-> 访问、stdlib 头 | 待开始 |
| M3 | 编写 bootstrap/compiler.c（词法 + 语法 + IR + codegen）| 待开始 |
| M4 | g0 编译 compiler.c 成功（g1 可运行） | 待开始 |
| M5 | g1 编译 compiler.c 成功（g2 可运行，自举一阶段） | 待开始 |
| M6 | g2 == g3，自举完全稳定 | 待开始 |

---

## 技术风险与应对

| 风险 | 说明 | 应对 |
|------|------|------|
| struct 支持复杂度高 | parser/codegen 均需大改 | 先用 parallel arrays 方案验证可行性，再引入 struct |
| 外部函数调用的参数类型匹配 | 语义检查需放宽 | 将未声明函数视为 extern，跳过 arity 检查 |
| 生成 C 的可读性 | compiler.c 生成的 C 须经 clang 接受 | 沿用 Python 编译器的现有生成策略 |
| 三阶段二进制不一致 | 编译器 bug 导致 g2 ≠ g3 | 用小测试用例逐步缩小问题范围 |

---

## 不在本次重构范围内

- 本机汇编后端（仍沿用输出 C → 调用 clang 的策略）
- 完整 C 标准支持（`union`、`enum`、位域、浮点、VLA 等）
- 增量编译与链接
- 调试信息（DWARF）
