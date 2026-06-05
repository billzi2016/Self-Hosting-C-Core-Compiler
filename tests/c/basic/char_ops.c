extern int printf(char *fmt, ...);
extern int strlen(char *s);

int main() {
    char str[16];
    int vowels;
    int i;
    char c;

    str[0] = 'H';
    str[1] = 'e';
    str[2] = 'l';
    str[3] = 'l';
    str[4] = 'o';
    str[5] = ' ';
    str[6] = 'W';
    str[7] = 'o';
    str[8] = 'r';
    str[9] = 'l';
    str[10] = 'd';
    str[11] = 0;

    vowels = 0;
    i = 0;
    while (str[i] != 0) {
        c = str[i];
        if (c == 'a' || c == 'e' || c == 'i' || c == 'o' || c == 'u' ||
            c == 'A' || c == 'E' || c == 'I' || c == 'O' || c == 'U') {
            vowels = vowels + 1;
        }
        i = i + 1;
    }
    printf("vowels: %d\n", vowels);
    return 0;
}
