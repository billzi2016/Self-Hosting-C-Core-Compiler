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

## 当前已支持的扩展能力

- `char`
- 字符字面量
- 字符串字面量
- 固定长度数组声明
- 数组索引
- 基础指针声明
- `&` 取地址
- `*` 解引用

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

如果你想直接看到标准输出结果，建议运行带 `_stdout` 后缀的示例：

```bash
python3 -m c_core_compiler examples/fib_stdout.c -o build/fib_stdout
./build/fib_stdout
```

如果你想看“一眼就知道对不对”的展示型输出，建议运行完整序列版本：

```bash
python3 -m c_core_compiler examples/fib_sequence_stdout.c -o build/fib_sequence_stdout
./build/fib_sequence_stdout
```

## `return` 与 `stdout` 的区别

这个项目里的示例分成两类，目的不同：

- `return` 型示例：通过进程退出码表达结果，更适合做编译器正确性验证、脚本检查和自动化测试
- `stdout` 型示例：通过标准输出直接打印结果，更适合给人看，也更适合公开展示

对应到构建结果目录就是：

- `build/results_return/`：重点看 `exit.txt`
- `build/results_stdout/`：重点看 `stdout.txt`

例如：

- `fib.c` 的结果是 `return fib(6);`，所以退出码是 `8`
- `fib_sequence_stdout.c` 会把 `1 1 2 3 5 8 13` 按行打印出来，因此更适合直接展示

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

## 示例运行命令

### 基础示例

`hello.c`

```bash
python3 -m c_core_compiler examples/hello.c -o build/hello
./build/hello
```

`factorial.c`

```bash
python3 -m c_core_compiler examples/factorial.c -o build/factorial
./build/factorial
```

`fib.c`

```bash
python3 -m c_core_compiler examples/fib.c -o build/fib
./build/fib
```

`control_flow_demo.c`

```bash
python3 -m c_core_compiler examples/control_flow_demo.c -o build/control_flow_demo
./build/control_flow_demo
```

`char_demo.c`

```bash
python3 -m c_core_compiler examples/char_demo.c -o build/char_demo
./build/char_demo
```

`array_demo.c`

```bash
python3 -m c_core_compiler examples/array_demo.c -o build/array_demo
./build/array_demo
```

`pointer_demo.c`

```bash
python3 -m c_core_compiler examples/pointer_demo.c -o build/pointer_demo
./build/pointer_demo
```

`string_demo.c`

```bash
python3 -m c_core_compiler examples/string_demo.c -o build/string_demo
./build/string_demo
```

### 带标准输出的示例

`hello_stdout.c`

```bash
python3 -m c_core_compiler examples/hello_stdout.c -o build/hello_stdout
./build/hello_stdout
```

`factorial_stdout.c`

```bash
python3 -m c_core_compiler examples/factorial_stdout.c -o build/factorial_stdout
./build/factorial_stdout
```

`fib_stdout.c`

```bash
python3 -m c_core_compiler examples/fib_stdout.c -o build/fib_stdout
./build/fib_stdout
```

`fib_sequence_stdout.c`

```bash
python3 -m c_core_compiler examples/fib_sequence_stdout.c -o build/fib_sequence_stdout
./build/fib_sequence_stdout
```

`control_flow_demo_stdout.c`

```bash
python3 -m c_core_compiler examples/control_flow_demo_stdout.c -o build/control_flow_demo_stdout
./build/control_flow_demo_stdout
```

`char_demo_stdout.c`

```bash
python3 -m c_core_compiler examples/char_demo_stdout.c -o build/char_demo_stdout
./build/char_demo_stdout
```

`array_demo_stdout.c`

```bash
python3 -m c_core_compiler examples/array_demo_stdout.c -o build/array_demo_stdout
./build/array_demo_stdout
```

`pointer_demo_stdout.c`

```bash
python3 -m c_core_compiler examples/pointer_demo_stdout.c -o build/pointer_demo_stdout
./build/pointer_demo_stdout
```

`string_demo_stdout.c`

```bash
python3 -m c_core_compiler examples/string_demo_stdout.c -o build/string_demo_stdout
./build/string_demo_stdout
```

## 批量运行全部示例

批量编译并运行全部基础示例，并把结果分别保存到 `build/results_return/<示例名>/`：

```bash
mkdir -p build/results_return
for f in examples/*.c; do
  if [[ "$f" == *_stdout.c ]]; then
    continue
  fi
  name=$(basename "$f" .c)
  mkdir -p "build/results_return/$name"
  PYTHONPATH=src python3 -m c_core_compiler "$f" -o "build/results_return/$name/program"
  "build/results_return/$name/program" > "build/results_return/$name/stdout.txt" 2> "build/results_return/$name/stderr.txt"
  printf "%s\n" "$?" > "build/results_return/$name/exit.txt"
done
```

批量编译并运行全部带标准输出的示例，并把结果分别保存到 `build/results_stdout/<示例名>/`：

```bash
mkdir -p build/results_stdout
for f in examples/*_stdout.c; do
  name=$(basename "$f" .c)
  mkdir -p "build/results_stdout/$name"
  PYTHONPATH=src python3 -m c_core_compiler "$f" -o "build/results_stdout/$name/program"
  "build/results_stdout/$name/program" > "build/results_stdout/$name/stdout.txt" 2> "build/results_stdout/$name/stderr.txt"
  printf "%s\n" "$?" > "build/results_stdout/$name/exit.txt"
done
```

## 示例结果文件

这里有一个很重要的区别：

- `return`
  - 表示程序退出码
  - 更适合做验证型示例
  - 适合测试“程序最终算出来的值对不对”

- `stdout`
  - 表示程序打印到标准输出的内容
  - 更适合做展示型示例
  - 适合直接展示“程序运行后给人看的结果是什么”

因此：

- `build/results_return/` 主要看退出码
- `build/results_stdout/` 主要看标准输出

基础示例运行结果保存在：

- `build/results_return/`
- 每个示例一个子目录，例如：`build/results_return/factorial/`
- 总表：`build/results_return/run_results.txt`

带标准输出的示例运行结果保存在：

- `build/results_stdout/`
- 每个示例一个子目录，例如：`build/results_stdout/fib_sequence_stdout/`
- 总表：`build/results_stdout/run_results.txt`

如果你想看最适合公开展示的结果，优先看：

- `examples/fib_sequence_stdout.c`
- 结果文件：`build/results_stdout/fib_sequence_stdout/stdout.txt`

## 目录说明

- `src/c_core_compiler/`：编译器实现
- `tests/`：单元测试、快照测试与端到端测试
- `examples/`：用于演示和回归的示例程序
- `PRD.md`：项目范围与目标
- `TASKS.md`：一期、二期任务清单
- `ARCHITECTURE.md`：模块设计与数据流
- `TESTING.md`：测试策略与覆盖说明
- `CONTRIBUTING.md`：协作与提交规范
- `DEVELOPMENT.md`：开发流程与模块说明
- `RELEASE.md`：版本摘要与限制
- `EXAMPLES.md`：示例说明与常用命令

## 致谢

感谢《编译原理》这本书，它帮助我建立了更系统的编译器知识框架。

感谢 `https://pandolia.net/tinyc/`，它让我对编译原理有了更深入的实践性理解，也帮助我更清楚地思考如何把编译流程拆成可实现、可验证、可持续迭代的工程结构。
