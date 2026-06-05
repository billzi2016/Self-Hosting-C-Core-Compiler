# Development

## 开发原则

当前项目采用分阶段开发方式：

1. 先确认语法和数据结构是否能承载目标特性
2. 再补语义检查
3. 然后让后端真正可编译
4. 最后补测试和文档

不要反过来做。否则最容易出现“表面支持，实际不可用”的半成品。

## 当前编译链路

### 标准整数子集

```text
source -> lexer -> parser -> semantic -> IR -> optimizer -> IR backend -> executable
```

### 高级语言特性

当源码包含以下能力时，会走 AST 规范化 C 后端：

- `char`
- 字符串字面量
- 数组
- 基础指针
- `&` 取地址
- `*` 解引用
- `[]` 索引

路径如下：

```text
source -> lexer -> parser -> semantic -> AST backend -> executable
```

这样做的原因是：

- 先把语言能力做实
- 不强迫现有 IR 一次性承载所有高级语义
- 保持现有整数子集的 IR/优化链路稳定

## 主要模块

- `lexer.py`：字符流转 Token
- `parser.py`：Token 转 AST
- `semantic.py`：名称解析与基础规则检查
- `ir_builder.py`：整数子集下降到 IR
- `optimizer.py`：保守优化
- `codegen/_portable_c.py`：后端代码生成
- `toolchain.py`：调用系统编译器

## 本地验证

运行全部测试：

```bash
python3 -B -m unittest discover -s tests -v
```

输出 AST：

```bash
python3 -m c_core_compiler examples/hello.c --emit-ast
```

输出 IR：

```bash
python3 -m c_core_compiler examples/control_flow_demo.c --emit-ir
```

输出 IR 控制流图：

```bash
python3 -m c_core_compiler examples/control_flow_demo.c --emit-ir-dot
```

编译高级特性示例：

```bash
python3 -m c_core_compiler examples/pointer_demo.c -o build/pointer_demo
```

## 后续建议顺序

如果继续扩展语言，建议顺序如下：

1. `char` 与字符串相关能力
2. 数组与索引
3. 基础指针
4. 更完整类型系统
5. 再考虑让高级特性进入 IR
