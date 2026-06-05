extern int printf(char *fmt, ...);

void two_sum(int *arr, int size, int target) {
    int i;
    int j;

    i = 0;
    while (i < size) {
        j = i + 1;
        while (j < size) {
            if (arr[i] + arr[j] == target) {
                printf("target %d: [%d,%d]\n", target, i, j);
                return;
            }
            j = j + 1;
        }
        i = i + 1;
    }
}

int main() {
    int arr1[4];
    int arr2[3];
    int arr3[2];

    arr1[0] = 2;
    arr1[1] = 7;
    arr1[2] = 11;
    arr1[3] = 15;
    two_sum(arr1, 4, 9);

    arr2[0] = 3;
    arr2[1] = 2;
    arr2[2] = 4;
    two_sum(arr2, 3, 6);

    arr3[0] = 3;
    arr3[1] = 3;
    two_sum(arr3, 2, 6);

    return 0;
}
