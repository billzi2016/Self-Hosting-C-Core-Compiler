char next_char(char value) {
    return value + 1;
}

int main() {
    char c = 'A';
    print_int(next_char(c) - 'A');
    return 0;
}
