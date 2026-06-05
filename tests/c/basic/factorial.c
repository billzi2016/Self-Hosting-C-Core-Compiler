extern int printf(char *fmt, ...);

int factorial(int n) {
    int result;
    result = 1;
    while (n > 1) {
        result = result * n;
        n = n - 1;
    }
    return result;
}

int main() {
    int i;
    i = 1;
    while (i <= 10) {
        printf("%d! = %d\n", i, factorial(i));
        i = i + 1;
    }
    return 0;
}
