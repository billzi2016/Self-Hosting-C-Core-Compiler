extern int printf(char *fmt, ...);

int main() {
    int arr[9];
    int max_sum;
    int cur_sum;
    int i;

    arr[0] = -2;
    arr[1] = 1;
    arr[2] = -3;
    arr[3] = 4;
    arr[4] = -1;
    arr[5] = 2;
    arr[6] = 1;
    arr[7] = -5;
    arr[8] = 4;

    max_sum = arr[0];
    cur_sum = arr[0];
    i = 1;
    while (i < 9) {
        if (cur_sum + arr[i] > arr[i]) {
            cur_sum = cur_sum + arr[i];
        } else {
            cur_sum = arr[i];
        }
        if (cur_sum > max_sum) {
            max_sum = cur_sum;
        }
        i = i + 1;
    }

    printf("max subarray sum: %d\n", max_sum);
    return 0;
}
