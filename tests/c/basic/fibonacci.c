extern int printf(char *fmt, ...);

int fib(int n) {
    if (n <= 1) {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

int main() {
    int i;
    i = 1;
    while (i <= 10) {
        printf("fib(%d) = %d\n", i, fib(i));
        i = i + 1;
    }
    return 0;
}
