#!/bin/bash
# Usage: ./tests/run_c_tests.sh [compiler_binary]
# Default compiler: build/compiler_native

COMPILER_BIN="${1:-build/compiler_native}"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

PASS=0
FAIL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

run_test() {
    local src="$1"
    local expected="${src%.c}.expected"
    local test_name
    test_name="$(basename "$src" .c)"

    if [ ! -f "$expected" ]; then
        printf "${RED}FAIL${NC}  %s  (no .expected file)\n" "$test_name"
        FAIL=$((FAIL + 1))
        return
    fi

    "$COMPILER_BIN" "$src" -o /tmp/test_bin 2>/tmp/test_compile_err
    if [ $? -ne 0 ]; then
        printf "${RED}FAIL${NC}  %s  (compile error)\n" "$test_name"
        FAIL=$((FAIL + 1))
        return
    fi

    actual=$(/tmp/test_bin 2>/dev/null)
    expected_content=$(cat "$expected")

    if [ "$actual" = "$expected_content" ]; then
        printf "${GREEN}PASS${NC}  %s\n" "$test_name"
        PASS=$((PASS + 1))
    else
        printf "${RED}FAIL${NC}  %s\n" "$test_name"
        printf "  expected: %s\n" "$expected_content"
        printf "  actual:   %s\n" "$actual"
        FAIL=$((FAIL + 1))
    fi
}

echo "Running C tests with compiler: $COMPILER_BIN"
echo "----------------------------------------"

for src in "$SCRIPT_DIR/c/basic/"*.c; do
    [ -f "$src" ] && run_test "$src"
done

for src in "$SCRIPT_DIR/c/leetcode/"*.c; do
    [ -f "$src" ] && run_test "$src"
done

echo "----------------------------------------"
echo "Results: $PASS passed, $FAIL failed"

if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
exit 0
