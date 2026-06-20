#include <stdio.h>

int main() {
    int a, b;
    char op;

    scanf("%d %c %d", &a, &op, &b);

    /* ERROR: 'resultado' no fue declarado.
       GCC va a reportar: error: 'resultado' undeclared
       Este error aparece igual en Code::Blocks y en el AutoCorrector. */
    resultado = a + b;
    printf("%d\n", resultado);

    return 0;
}
