# Self-Hosting C Core Compiler

用 Python 实现的 C 子集编译器，目标是**自举（self-hosting）**：用这个编译器本身编译自己的 C 源码，最终脱离 Python 运行时。

## 项目状态

```
Gen 0 (g0): Python 编译器  →  编译 bootstrap/compiler.c  →  compiler_g1
Gen 1 (g1): C 二进制       →  编译 bootstrap/compiler.c  →  compiler_g2
Gen 2 (g2): C 二进制       →  编译 bootstrap/compiler.c  →  compiler_g3
验证：compiler_g2 == compiler_g3  →  自举成立 ✓
```

| 里程碑 | 内容 | 状态 |
|--------|------|------|
| M0 | 整理文档，写自举 PRD | ✅ |
| M1 | 扩展 Python 编译器（void/struct/typedef/extern/++/cast/sizeof/hex） | ✅ |
| M2 | 编写 `bootstrap/compiler.c` | ✅ |
| M3 | 建立测试套件（basic + LeetCode），15/15 通过 | ✅ |
| M4 | g0 编译 compiler.c 成功（g1 可运行） | ✅ |
| M5 | g1 编译 compiler.c 成功（g2 可运行） | ✅ |
| M6 | g2 == g3，自举完全稳定 | ✅ |

---

## 目录结构

```
Self-Hosting-C-Core-Compiler/
├── python_host/            ← Gen 0：Python 编译器（永久保留为 bootstrap 工具）
│   ├── src/c_core_compiler/
│   └── tests/              ← Python 单元测试（50 个，全通过）
├── bootstrap/
│   ├── compiler.c          ← Gen 1 源码：用 C 子集写的编译器
│   └── bootstrap.sh        ← 三代自举验证脚本
├── tests/
│   ├── c/
│   │   ├── basic/          ← 7 个基础 C 程序 + .expected 预期输出
│   │   └── leetcode/       ← 8 个 LeetCode 风格 C 程序 + .expected 预期输出
│   └── run_c_tests.sh      ← C 程序测试运行脚本
├── examples/               ← 早期演示程序
├── old/                    ← 归档文档
├── REFACTOR_PRD.md         ← 自举重构计划
└── SELF_HOSTING.md         ← 自举流程说明
```

---

## 快速开始

### 运行测试

```bash
# C 程序测试（使用原生编译器，15/15）
./tests/run_c_tests.sh build/compiler_native

# Python 单元测试（50 个）
cd python_host && python3 -m pytest tests/ -v
```

### 用原生编译器编译 C 程序

先构建原生编译器：

```bash
clang -o build/compiler_native bootstrap/compiler.c
```

然后编译任意测试程序：

```bash
./build/compiler_native tests/c/basic/factorial.c -o build/factorial
./build/factorial
```

### 用 Python 编译器编译

```bash
cd python_host
python3 -m c_core_compiler ../tests/c/basic/hello.c -o ../build/hello
../build/hello
```

### 编译所有示例

```bash
# 编译 examples/ 下的全部 .c 文件到 build/examples/
./build_examples.sh
```

### 运行自举脚本

```bash
# Gen0(Python)→g1→g2→g3，验证 g2/g3 输出相同
bash bootstrap/bootstrap.sh
```

---

## 支持的 C 子集

Python 编译器（Gen 0）和 C 编译器（Gen 1）均支持以下特性：

**类型**
- `int`、`char`、`void`
- 指针（`*`、`&`、解引用）
- 固定长度数组 `int arr[N]`
- `struct` / `typedef struct`

**语句**
- `if` / `else`
- `while`、`for`
- `break`、`continue`
- `return`（含 void 函数的 `return;`）
- 局部变量声明

**表达式**
- 算术：`+ - * / %`
- 比较：`== != < <= > >=`
- 逻辑：`&& ||`
- 位运算：`& | ^ ~ << >>`
- 赋值：`= += -= *= /=`
- 前缀/后缀 `++ --`
- 强制类型转换 `(Type)expr`
- `sizeof(Type)`
- 成员访问 `.` 和 `->`
- 三目运算符 `a ? b : c`
- 十六进制字面量 `0x...`

**其他**
- `extern` 函数声明（调用标准库）
- 变参函数 `...`
- 多行注释、单行注释

---

## 测试套件

### basic（基础功能）

| 测试 | 内容 |
|------|------|
| `hello` | Hello World 输出 |
| `factorial` | 循环计算 1!~10! |
| `fibonacci` | 递归斐波那契 fib(1)~fib(10) |
| `array` | 固定数组赋值与求和 |
| `control_flow` | FizzBuzz 1-20 |
| `pointer` | 指针交换 swap(a, b) |
| `char_ops` | 逐字符遍历统计元音 |

### leetcode（算法题）

| 测试 | 对应题目 |
|------|---------|
| `fizzbuzz` | FizzBuzz 1-30 |
| `binary_search` | LC #704 二分查找 |
| `bubble_sort` | 冒泡排序 |
| `max_subarray` | LC #53 最大子数组和（Kadane） |
| `palindrome` | LC #9 回文数 |
| `climb_stairs` | LC #70 爬楼梯（DP） |
| `two_sum` | LC #1 两数之和（O(n²)） |
| `reverse_string` | LC #344 反转字符串 |

---

## 编译流程

### Python 编译器（Gen 0）

```
.c 源码
  → Lexer（词法分析）
  → Parser（递归下降，生成 AST）
  → Semantic Analyzer（符号检查）
  → IR Builder（三地址 IR）
  → IR Optimizer
  → Codegen（输出规范化 C）
  → clang → 可执行文件
```

### C 编译器（Gen 1，bootstrap/compiler.c）

```
.c 源码
  → Lexer（手写，静态 Token 数组）
  → Parser（递归下降，链表式 AST）
  → Codegen（输出规范化 C）
  → clang → 可执行文件
```

---

## Python 编译器常用命令

```bash
cd python_host

# 输出 Token 序列
python3 -m c_core_compiler ../tests/c/basic/hello.c --emit-tokens

# 输出 AST
python3 -m c_core_compiler ../tests/c/basic/hello.c --emit-ast

# 输出 IR
python3 -m c_core_compiler ../tests/c/basic/hello.c --emit-ir

# 输出生成的 C 代码
python3 -m c_core_compiler ../tests/c/basic/hello.c --emit-c
```

---

## 致谢

感谢《编译原理》和 [tinyc](https://pandolia.net/tinyc/) 提供的思路与参考。
