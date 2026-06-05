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
echo "=== Step 4: Verifying g2 == g3 ==="
if diff "$BUILD/compiler_g2" "$BUILD/compiler_g3" > /dev/null 2>&1; then
    echo "SUCCESS: compiler_g2 == compiler_g3, self-hosting verified."
else
    echo "FAIL: compiler_g2 != compiler_g3, self-hosting not yet stable."
    exit 1
fi
