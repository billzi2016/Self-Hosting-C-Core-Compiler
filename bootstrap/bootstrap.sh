#!/bin/bash
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$REPO_ROOT/build"
COMPILER_C="$REPO_ROOT/bootstrap/compiler.c"

mkdir -p "$BUILD"

echo "=== Step 1: Gen 0 (Python) compiling compiler.c -> compiler_g1 ==="
cd "$REPO_ROOT/python_host"
python3 -m c_core_compiler "$COMPILER_C" -o "$BUILD/compiler_g1"
echo "compiler_g1 built."

echo ""
echo "=== Step 2: Gen 1 compiling compiler.c -> compiler_g2 ==="
"$BUILD/compiler_g1" "$COMPILER_C" -o "$BUILD/compiler_g2"
echo "compiler_g2 built."

echo ""
echo "=== Step 3: Gen 2 compiling compiler.c -> compiler_g3 ==="
"$BUILD/compiler_g2" "$COMPILER_C" -o "$BUILD/compiler_g3"
echo "compiler_g3 built."

echo ""
echo "=== Step 4: Verifying g2 and g3 produce identical output ==="
"$BUILD/compiler_g2" "$COMPILER_C" -o /tmp/_g2_verify 2>/dev/null
cp /tmp/_cc_generated.c /tmp/_g2_generated.c
"$BUILD/compiler_g3" "$COMPILER_C" -o /tmp/_g3_verify 2>/dev/null
cp /tmp/_cc_generated.c /tmp/_g3_generated.c
if diff /tmp/_g2_generated.c /tmp/_g3_generated.c > /dev/null 2>&1; then
    echo "SUCCESS: g2 and g3 generate identical C code — self-hosting verified."
else
    echo "FAIL: g2 and g3 generate different C code."
    diff /tmp/_g2_generated.c /tmp/_g3_generated.c | head -20
    exit 1
fi
