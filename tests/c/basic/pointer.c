extern int printf(char *fmt, ...);

void swap(int *a, int *b) {
    int tmp;
    tmp = *a;
    *a = *b;
    *b = tmp;
}

int main() {
    int a;
    int b;
    a = 5;
    b = 3;
    printf("before: a=%d b=%d\n", a, b);
    swap(&a, &b);
    printf("after:  a=%d b=%d\n", a, b);
    return 0;
}
