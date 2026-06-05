extern int printf(char *fmt, ...);

int main() {
    int dp[12];
    int i;

    dp[0] = 0;
    dp[1] = 1;
    dp[2] = 2;

    i = 3;
    while (i <= 10) {
        dp[i] = dp[i - 1] + dp[i - 2];
        i = i + 1;
    }

    i = 1;
    while (i <= 10) {
        printf("stairs(%d) = %d\n", i, dp[i]);
        i = i + 1;
    }

    return 0;
}
