# Demo — Calculadora básica en C

Consigna de prueba para validar el flujo completo del AutoCorrector IA.

## Estructura

```
demo-consigna-calculadora/
├── consigna/
│   ├── consigna.md          ← enunciado completo y criterios
│   └── casos_prueba.json    ← casos con input/output/explicación
├── entregas/
│   ├── entrega_correcta/
│   │   └── main.c           ← compila y pasa los 5 tests (11/11 pts)
│   ├── entrega_error_compilacion/
│   │   └── main.c           ← falla al compilar (variable no declarada)
│   └── entrega_error_logico/
│       └── main.c           ← compila pero pasa solo 1 de 5 tests
├── seed_demo.py             ← carga la consigna en la DB
└── README.md
```

## Paso 1 — Cargar la consigna en la DB

Desde la carpeta `service/`:

```bash
poetry run python ../demo-consigna-calculadora/seed_demo.py
```

Verifica que la consigna aparece en: http://localhost:8000/api/consignas

## Paso 2 — Probar con la entrega correcta

1. Comprimir `entregas/entrega_correcta/` en un ZIP (el archivo `main.c` debe estar en la raíz del ZIP).
2. En el AutoCorrector, seleccionar la consigna "TP Demo - Calculadora básica en C".
3. Subir el ZIP.

**Resultado esperado:** compilación exitosa, 5/5 tests pasan, score 11/11, `cumple_consigna = true`.

## Paso 3 — Probar con error de compilación

1. Comprimir `entregas/entrega_error_compilacion/` en un ZIP.
2. Subir al AutoCorrector con la misma consigna.

**Resultado esperado:** compilación fallida con error `'resultado' undeclared`. No se ejecutan tests. Score 0.

**Error exacto que muestra GCC (igual en Code::Blocks):**
```
main.c:10:5: error: 'resultado' undeclared (first use in this function)
```

## Paso 4 — Probar con error lógico

1. Comprimir `entregas/entrega_error_logico/` en un ZIP.
2. Subir al AutoCorrector con la misma consigna.

**Resultado esperado:** compila sin errores, pero:

| Test                     | Entrada  | Esperado                | Obtiene | Resultado |
|--------------------------|----------|-------------------------|---------|-----------|
| Suma básica              | `3 + 5`  | `8`                     | `8`     | PASS      |
| Resta                    | `10 - 3` | `7`                     | `13`    | FAIL      |
| Multiplicación           | `4 * 6`  | `24`                    | `10`    | FAIL      |
| División exacta          | `15 / 3` | `5`                     | `18`    | FAIL      |
| División por cero        | `7 / 0`  | `Error: division por cero` | `7` | FAIL      |

Score esperado: 2/11, `cumple_consigna = false`.

## Cómo crear los ZIPs (Windows)

En PowerShell, desde la carpeta `demo-consigna-calculadora/`:

```powershell
# Entrega correcta
Compress-Archive -Path entregas\entrega_correcta\main.c -DestinationPath entrega_correcta.zip -Force

# Error de compilación
Compress-Archive -Path entregas\entrega_error_compilacion\main.c -DestinationPath entrega_error_compilacion.zip -Force

# Error lógico
Compress-Archive -Path entregas\entrega_error_logico\main.c -DestinationPath entrega_error_logico.zip -Force
```

Los tres ZIPs quedan listos para subir desde el frontend.
