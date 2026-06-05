int main() {
    int sum = 0;
    int i = 0;
    for (i = 0; i < 5; i = i + 1) {
        if (i % 2 == 0) {
            sum = sum + i;
        } else {
            sum = sum + 1;
        }
    }
    print_int(sum);
    return 0;
}
