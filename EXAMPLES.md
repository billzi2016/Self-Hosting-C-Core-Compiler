# Examples

## 基础示例

### `examples/hello.c`

最小可运行程序，用来验证主链路是否正常。

### `examples/factorial.c`

验证函数调用、局部变量和 `while`。

### `examples/fib.c`

验证递归调用。

### `examples/control_flow_demo.c`

验证 `for`、`if / else`、取模和累加流程。

## 语言扩展示例

### `examples/char_demo.c`

验证 `char` 参数、`char` 局部变量和字符字面量。

### `examples/array_demo.c`

验证固定长度数组声明和索引读写。

### `examples/pointer_demo.c`

验证基础指针声明、`&` 取地址和 `*` 解引用。

### `examples/string_demo.c`

验证字符串字面量和字符指针索引。

## 带标准输出的示例

这些文件和原始示例逻辑基本一致，但会调用内建函数 `print_int(int)`，
把结果直接打印到标准输出，便于公开展示和手工验证：

- `examples/hello_stdout.c`
- `examples/factorial_stdout.c`
- `examples/fib_stdout.c`
- `examples/control_flow_demo_stdout.c`
- `examples/char_demo_stdout.c`
- `examples/array_demo_stdout.c`
- `examples/pointer_demo_stdout.c`
- `examples/string_demo_stdout.c`

## 常用命令

编译普通示例：

```bash
python3 -m c_core_compiler examples/hello.c -o build/hello
```

编译指针示例：

```bash
python3 -m c_core_compiler examples/pointer_demo.c -o build/pointer_demo
```

编译并运行带输出的指针示例：

```bash
python3 -m c_core_compiler examples/pointer_demo_stdout.c -o build/pointer_demo_stdout
./build/pointer_demo_stdout
```

输出 IR：

```bash
python3 -m c_core_compiler examples/control_flow_demo.c --emit-ir
```

输出 IR 控制流图：

```bash
python3 -m c_core_compiler examples/control_flow_demo.c --emit-ir-dot
```
