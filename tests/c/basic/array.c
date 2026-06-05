extern int printf(char *fmt, ...);

int main() {
    int arr[5];
    int sum;
    int i;

    arr[0] = 10;
    arr[1] = 20;
    arr[2] = 30;
    arr[3] = 40;
    arr[4] = 50;

    i = 0;
    while (i < 5) {
        printf("arr[%d] = %d\n", i, arr[i]);
        i = i + 1;
    }

    sum = 0;
    i = 0;
    while (i < 5) {
        sum = sum + arr[i];
        i = i + 1;
    }
    printf("sum = %d\n", sum);

    return 0;
}
