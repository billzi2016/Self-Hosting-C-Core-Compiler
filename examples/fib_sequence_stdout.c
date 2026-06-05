int fib(int n) {
    if (n < 2) {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

int main() {
    int i = 1;
    while (i <= 7) {
        print_int(fib(i));
        i = i + 1;
    }
    return 0;
}
