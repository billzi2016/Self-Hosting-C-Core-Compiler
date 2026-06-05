extern int printf(char *fmt, ...);

int main() {
    int arr[7];
    int i;
    int j;
    int tmp;
    int n;

    arr[0] = 64;
    arr[1] = 34;
    arr[2] = 25;
    arr[3] = 12;
    arr[4] = 22;
    arr[5] = 11;
    arr[6] = 90;

    n = 7;
    i = 0;
    while (i < n - 1) {
        j = 0;
        while (j < n - 1 - i) {
            if (arr[j] > arr[j + 1]) {
                tmp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = tmp;
            }
            j = j + 1;
        }
        i = i + 1;
    }

    printf("sorted:");
    i = 0;
    while (i < n) {
        printf(" %d", arr[i]);
        i = i + 1;
    }
    printf("\n");

    return 0;
}
