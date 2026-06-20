#include <stdio.h>

int main() {
    int a, b;
    char op;

    scanf("%d %c %d", &a, &op, &b);

    switch (op) {
        case '+':
            printf("%d\n", a + b);
            break;
        case '-':
            printf("%d\n", a - b);
            break;
        case '*':
            printf("%d\n", a * b);
            break;
        case '/':
            if (b == 0)
                printf("Error: division por cero\n");
            else
                printf("%d\n", a / b);
            break;
        default:
            printf("Operador invalido\n");
    }

    return 0;
}
