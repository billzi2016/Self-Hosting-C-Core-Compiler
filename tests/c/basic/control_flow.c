extern int printf(char *fmt, ...);

int main() {
    int i;
    i = 1;
    while (i <= 20) {
        if (i % 3 == 0 && i % 5 == 0) {
            printf("FizzBuzz\n");
        } else if (i % 3 == 0) {
            printf("Fizz\n");
        } else if (i % 5 == 0) {
            printf("Buzz\n");
        } else {
            printf("%d\n", i);
        }
        i = i + 1;
    }
    return 0;
}
