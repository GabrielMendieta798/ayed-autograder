# TP Demo — Calculadora básica en C

## Enunciado

Escribir un programa en C que lea desde la entrada estándar dos números enteros y un operador aritmético, e imprima el resultado.

### Formato de entrada

Una sola línea con el formato:

```
A op B
```

donde:
- `A` y `B` son enteros (pueden ser negativos)
- `op` es uno de: `+`, `-`, `*`, `/`

### Formato de salida

- Para `+`, `-`, `*`: imprimir el resultado como entero seguido de salto de línea.
- Para `/`: si `B == 0`, imprimir exactamente `Error: division por cero`. Caso contrario, imprimir el cociente entero.

### Ejemplos

| Entrada  | Salida                  |
|----------|-------------------------|
| `3 + 5`  | `8`                     |
| `10 - 3` | `7`                     |
| `4 * 6`  | `24`                    |
| `15 / 3` | `5`                     |
| `7 / 0`  | `Error: division por cero` |

## Criterios de corrección

| Criterio                         | Tipo          | Puntaje |
|----------------------------------|---------------|---------|
| Suma correcta (3 + 5 = 8)        | I/O test      | 2 pts   |
| Resta correcta (10 - 3 = 7)      | I/O test      | 2 pts   |
| Multiplicación correcta (4 * 6)  | I/O test      | 2 pts   |
| División exacta (15 / 3 = 5)     | I/O test      | 2 pts   |
| División por cero detectada      | I/O test      | 3 pts   |
| Usa `scanf`                      | Check estático| —       |
| Usa `printf`                     | Check estático| —       |

**Puntaje máximo: 11 puntos**

Los checks estáticos no suman puntos pero son obligatorios: si no están presentes, la corrección falla independientemente de los tests.

## Restricciones

- Solo `stdio.h`. No usar `math.h` ni otras librerías.
- El programa debe terminar con código de salida 0.
- No usar variables globales.
