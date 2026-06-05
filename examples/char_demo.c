char twice(char value) {
    return value + value;
}

int main() {
    char c = 'A';
    return twice(c) - 'A';
}
