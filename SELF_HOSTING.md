# 自举（Self-Hosting）说明

## 当前状态

```
源码(.c) → Python词法器 → Python语法器 → IR → 生成规范化C → 调用 clang → 可执行文件
```

编译器本身是 Python 写的，目标是让它变成用 **C 语言写的**，并且能编译自己。

---

## 自举三阶段流程

```
Gen 0 (g0) = 现有 Python 编译器
  ↓ 编译 compiler.c
Gen 1 (g1) = 第一个 C 编译器二进制
  ↓ 编译 compiler.c
Gen 2 (g2) = 第二个 C 编译器二进制
  ↓ 编译 compiler.c
Gen 3 (g3) = 第三个 C 编译器二进制

验证：g2 == g3 → 自举稳定 ✓
```

---

## 问题：现在的 Python 编译器还不能编译写编译器所需的 C 代码

写一个 C 编译器需要这些语言特性，**现在缺失**：

| 缺失特性 | 用途 |
|---------|------|
| `void` 类型 | 无返回值的函数 |
| `struct` / `typedef` | Token、AST 节点等数据结构 |
| 后缀 `++` / `--` | 循环计数器 |
| `break` / `continue` | 循环控制 |
| 类型转换 `(int *)ptr` | malloc 返回值 |
| 十六进制字面量 `0x41` | token kind 枚举值 |
| 外部函数调用（`malloc`、`strcmp` 等）| 标准库 |
| 结构体成员访问 `.` 和 `->` | 访问 AST 字段 |
| `sizeof` 运算符 | 内存分配大小 |

---

## 工作分三步

### M1 — 扩展 Python 编译器

让它支持上表中缺失的语言特性，使其具备编译一个 C 编译器源码的能力。

### M2 — 用 C 写 `bootstrap/compiler.c`

在扩展后支持的 C 子集内，实现：

- 词法分析（Lexer）
- 语法分析（Parser）
- 中间表示（IR）
- 代码生成（Codegen，输出规范化 C）
- 主函数：读文件 → 各阶段 → 输出 → 调用 clang

### M3 — 跑自举脚本 `bootstrap/bootstrap.sh`

```bash
# g0（Python）编译 compiler.c → g1
python -m c_core_compiler bootstrap/compiler.c -o build/compiler_g1

# g1 编译 compiler.c → g2
./build/compiler_g1 bootstrap/compiler.c -o build/compiler_g2

# g2 编译 compiler.c → g3
./build/compiler_g2 bootstrap/compiler.c -o build/compiler_g3

# 验证 g2 == g3，自举稳定
diff build/compiler_g2 build/compiler_g3 && echo "自举成立" || echo "自举失败"
```
