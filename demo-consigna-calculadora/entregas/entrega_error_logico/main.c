#include <stdio.h>

int main() {
    int a, b;
    char op;

    scanf("%d %c %d", &a, &op, &b);

    /* BUG: siempre suma, ignorando el operador op.
       Compila sin errores ni warnings.
       Pasa el test de suma (3 + 5 = 8), pero falla:
         - resta:           10 - 3 → imprime 13 en vez de 7
         - multiplicacion:   4 * 6 → imprime 10 en vez de 24
         - division:        15 / 3 → imprime 18 en vez de 5
         - division por 0:   7 / 0 → imprime 7  en vez del mensaje de error */
    printf("%d\n", a + b);

    return 0;
}
