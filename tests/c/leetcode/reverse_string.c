extern int printf(char *fmt, ...);
extern int strlen(char *s);

int main() {
    char str[16];
    int left;
    int right;
    int len;
    char tmp;

    str[0] = 'a';
    str[1] = 'b';
    str[2] = 'c';
    str[3] = 'd';
    str[4] = 'e';
    str[5] = 'f';
    str[6] = 'g';
    str[7] = 'h';
    str[8] = 0;

    left = 0;
    right = 7;
    while (left < right) {
        tmp = str[left];
        str[left] = str[right];
        str[right] = tmp;
        left = left + 1;
        right = right - 1;
    }

    printf("reversed: %s\n", str);
    return 0;
}
