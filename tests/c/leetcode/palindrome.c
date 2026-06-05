extern int printf(char *fmt, ...);

int is_palindrome(int x) {
    int orig;
    int rev;
    int tmp;

    if (x < 0) {
        return 0;
    }
    orig = x;
    rev = 0;
    tmp = x;
    while (tmp != 0) {
        rev = rev * 10 + tmp % 10;
        tmp = tmp / 10;
    }
    if (orig == rev) {
        return 1;
    }
    return 0;
}

int main() {
    if (is_palindrome(121)) {
        printf("121: yes\n");
    } else {
        printf("121: no\n");
    }

    if (is_palindrome(1221)) {
        printf("1221: yes\n");
    } else {
        printf("1221: no\n");
    }

    if (is_palindrome(12321)) {
        printf("12321: yes\n");
    } else {
        printf("12321: no\n");
    }

    if (is_palindrome(123)) {
        printf("123: yes\n");
    } else {
        printf("123: no\n");
    }

    if (is_palindrome(10)) {
        printf("10: yes\n");
    } else {
        printf("10: no\n");
    }

    return 0;
}
