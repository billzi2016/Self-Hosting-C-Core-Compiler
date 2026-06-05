#!/bin/bash
# 编译 examples/ 目录下的所有 .c 文件，输出到 build/examples/
set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON_HOST="$REPO_ROOT/python_host"
EXAMPLES_DIR="$REPO_ROOT/examples"
OUT_DIR="$REPO_ROOT/build/examples"

mkdir -p "$OUT_DIR"

PASS=0
FAIL=0

for src in "$EXAMPLES_DIR"/*.c; do
    name="$(basename "${src%.c}")"
    out="$OUT_DIR/$name"
    if (cd "$PYTHON_HOST" && python3 -m c_core_compiler "$src" -o "$out" 2>/dev/null); then
        echo "  BUILT  $name"
        PASS=$((PASS + 1))
    else
        echo "  FAIL   $name"
        FAIL=$((FAIL + 1))
    fi
done

echo ""
echo "结果：$PASS 成功 / $FAIL 失败"
