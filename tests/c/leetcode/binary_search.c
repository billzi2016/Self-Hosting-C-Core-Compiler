extern int printf(char *fmt, ...);

int binary_search(int *arr, int size, int target) {
    int left;
    int right;
    int mid;

    left = 0;
    right = size - 1;
    while (left <= right) {
        mid = (left + right) / 2;
        if (arr[mid] == target) {
            return mid;
        } else if (arr[mid] < target) {
            left = mid + 1;
        } else {
            right = mid - 1;
        }
    }
    return -1;
}

int main() {
    int arr[10];
    int result;

    arr[0] = 1;
    arr[1] = 3;
    arr[2] = 5;
    arr[3] = 7;
    arr[4] = 9;
    arr[5] = 11;
    arr[6] = 13;
    arr[7] = 15;
    arr[8] = 17;
    arr[9] = 19;

    result = binary_search(arr, 10, 7);
    if (result == -1) {
        printf("search 7: not found\n");
    } else {
        printf("search 7: index %d\n", result);
    }

    result = binary_search(arr, 10, 10);
    if (result == -1) {
        printf("search 10: not found\n");
    } else {
        printf("search 10: index %d\n", result);
    }

    result = binary_search(arr, 10, 19);
    if (result == -1) {
        printf("search 19: not found\n");
    } else {
        printf("search 19: index %d\n", result);
    }

    result = binary_search(arr, 10, 1);
    if (result == -1) {
        printf("search 1: not found\n");
    } else {
        printf("search 1: index %d\n", result);
    }

    return 0;
}
