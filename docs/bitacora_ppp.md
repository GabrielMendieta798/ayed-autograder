# Bitácora PPP — Corrector Automático AED
**Universidad Nacional de Lanús — Ingeniería en Sistemas**
**Última actualización: 2026-05-22**

---

## 1. Qué se implementó hoy (2026-05-22)

### Admin UI (feature principal)

Se construyó la interfaz de administración que permite al profesor crear y gestionar consignas sin tocar la base de datos directamente.

**Backend — `service/app/api/admin.py` (archivo nuevo):**
- 9 endpoints REST con prefijo `/api/admin/`
- CRUD completo para `Consigna`, `CasoPrueba` y `CheckEstatico`

**Backend — `service/app/models/schemas.py` (actualizado):**
- Nuevos schemas de entrada: `ConsignaIn`, `CasoPruebaIn`, `CheckEstaticoIn`
- Nuevo schema de salida: `CheckEstaticoOut` (movido antes de `ConsignaOut` por dependencia de orden)
- `ConsignaOut` ahora incluye `checks_estaticos` (antes solo tenía `casos_prueba`)

**Backend — `service/app/main.py` (actualizado):**
- Registro del nuevo router `admin_router` con prefijo `/api`

**Frontend — `frontend/src/components/AdminView.tsx` (archivo nuevo, ~340 líneas):**
- `ConsignaList`: lista todas las consignas, botón "Nueva consigna" con formulario inline
- `ConsignaDetail`: detalle de una consigna con edición de nombre/descripción/flags
- `CasosPanel`: lista casos de prueba, formulario para agregar/editar/eliminar
- `ChecksPanel`: lista checks estáticos, formulario para agregar/editar/eliminar

**Frontend — `frontend/src/App.tsx` (actualizado):**
- Navegación "Corrector / Admin" en el header
- Al volver del admin, recarga las consignas automáticamente

**Frontend — `frontend/src/types.ts` (actualizado):**
- Nuevas interfaces: `CasoPruebaOut`, `CheckEstaticoOut`, `ConsignaDetail`

**Commit del fix previo:** mejora del mensaje de error de compilación en `test_runner.py` y campos `points` en `seed.py`.

---

## 2. Archivos modificados/creados en la sesión actual

```
service/
  app/
    api/
      admin.py              ← NUEVO: endpoints CRUD del admin
      main.py               ← MODIFICADO: registra admin_router
    models/
      schemas.py            ← MODIFICADO: CheckEstaticoOut, ConsignaIn/CasoPruebaIn/CheckEstaticoIn
    services/
      test_runner.py        ← MODIFICADO: mensaje de error más descriptivo al fallar compilación
  seed.py                   ← MODIFICADO: agrega campo points a cada CasoPrueba

frontend/
  src/
    App.tsx                 ← MODIFICADO: navegación Corrector/Admin
    types.ts                ← MODIFICADO: nuevos tipos para admin
    components/
      AdminView.tsx         ← NUEVO: UI de administración completa
```

---

## 3. Endpoints actuales completos

### Públicos (alumnos y frontend)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Liveness check — devuelve `{"status": "ok"}` |
| `GET` | `/api/consignas` | Lista consignas activas ordenadas por nombre |
| `GET` | `/api/consignas/{id}` | Detalle de una consigna (incluye casos y checks) |
| `POST` | `/api/analizar` | Endpoint legacy — analiza un ZIP sin persistir en DB |
| `POST` | `/api/submissions/analyze` | Analiza un ZIP y persiste el resultado en DB |
| `GET` | `/api/submissions/{id}` | Recupera una submission ya procesada |

### Admin (profesor)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/admin/consignas` | Crear nueva consigna |
| `PUT` | `/api/admin/consignas/{id}` | Editar consigna existente |
| `DELETE` | `/api/admin/consignas/{id}` | Eliminar consigna (cascade: borra sus casos y checks) |
| `POST` | `/api/admin/consignas/{id}/casos` | Agregar caso de prueba a una consigna |
| `PUT` | `/api/admin/casos/{id}` | Editar caso de prueba |
| `DELETE` | `/api/admin/casos/{id}` | Eliminar caso de prueba |
| `POST` | `/api/admin/consignas/{id}/checks` | Agregar check estático a una consigna |
| `PUT` | `/api/admin/checks/{id}` | Editar check estático |
| `DELETE` | `/api/admin/checks/{id}` | Eliminar check estático |

> **Nota:** No hay autenticación todavía. Cualquiera con acceso al puerto 8000 puede usar los endpoints admin. Para MVP universitario interno esto es aceptable; a futuro requiere JWT o sesión.

---

## 4. Flujo completo del sistema

### 4.1 Consignas y configuración previa (rol: profesor)

Antes de que un alumno pueda subir su entrega, el profesor debe configurar la consigna. Hoy puede hacerlo de tres formas:

1. **Desde la Admin UI** en `localhost:5173` → pestaña "Admin"
2. **Corriendo `seed.py`** desde la carpeta `service/`
3. **Insertando directamente en la DB** con SQLite

Una consigna tiene:
- `nombre` y `descripcion` (texto libre que ve el alumno)
- Flags booleanos: `requires_tda`, `requires_void_pointer`, `requires_modularization`
- **`CheckEstatico`**: patrones regex que se buscan en el código fuente del alumno
- **`CasoPrueba`**: inputs que se le pasan al binario del alumno y outputs esperados

### 4.2 Subida del ZIP (rol: alumno)

El alumno abre `localhost:5173`, elige su consigna, escribe su nombre y sube un archivo `.zip` o `.rar` con sus archivos `.c` y `.h`.

`POST /api/submissions/analyze` recibe:
- `archivo`: el ZIP como `multipart/form-data`
- `consigna_id`: ID de la consigna seleccionada
- `nombre_alumno`: texto libre

### 4.3 Validación del ZIP — `zip_validator.py`

Antes de ejecutar nada, el ZIP pasa por controles de seguridad:

- Rechaza path traversal (`../malicioso.c`)
- Máximo 50 archivos
- Máximo 20 MB descomprimido
- Solo extensiones permitidas: `.c`, `.h`, `.cbp`, `.mk`, `makefile`
- Soporte RAR via `bsdtar` (en Windows: `tar.exe`)

Si falla cualquier control → HTTP 400 con descripción del error.

### 4.4 Checks estáticos — `static_analyzer.py`

Se leen todos los archivos `.c` y `.h` en una sola cadena y se corre `re.findall(pattern, source_code)` por cada `CheckEstatico` de la consigna.

- `check_type="exists"`: pasa si hay al menos 1 coincidencia
- `check_type="count_gte"`: pasa si hay al menos `min_count` coincidencias

Ejemplos reales de la consigna TP2:
- `void\s*\*` → detecta uso de punteros void
- `\(\s*\*\s*\w+\s*\)\s*\(` → detecta funciones callback
- `typedef\s+struct` con `count_gte=3` → detecta al menos 3 estructuras TDA

**Este paso NO usa Docker** — trabaja solo con el texto del código fuente.

### 4.5 Compilación — `compiler.py`

Se lanza un contenedor Docker efímero con la imagen `gcc:latest`:

```bash
docker run --rm \
  --memory=128m --cpus=0.5 --pids-limit=128 \
  --network=none --read-only --tmpfs /tmp:size=64m \
  --cap-drop=ALL --security-opt=no-new-privileges \
  -v {workdir}:/code -w /code \
  gcc:latest \
  gcc -std=c11 -Wall -o /code/out *.c
```

La salida de `stderr` se parsea con regex:
- Líneas con `"error:"` → lista `errors[]`
- Líneas con `"warning:"` → lista `warnings[]`

Si hay errores → `compilation.success = False`. Los tests I/O no se corren.

### 4.6 Tests I/O — `test_runner.py`

El binario compilado (`/code/out`) se ejecuta una vez por cada `CasoPrueba` con Docker:

```bash
docker run --rm -i \
  --memory=128m --cpus=0.5 --pids-limit=128 \
  --network=none --read-only --tmpfs /tmp:size=64m \
  --cap-drop=ALL --security-opt=no-new-privileges --user=1000:1000 \
  -v {workdir}:/code:ro \
  gcc:latest /code/out
```

El `input` del `CasoPrueba` se pasa por stdin. Luego se evalúa el resultado:

| `check_type` | Condición para pasar |
|---|---|
| `exitcode` | El proceso termina con código 0 (no crashea) |
| `contains` | `stdout` contiene `expected_output` (case-insensitive) |
| `exact` | `stdout.strip() == expected_output.strip()` |

Si el programa excede `timeout_seg` → falla con mensaje `"Timeout (Xs)"`.

### 4.7 Cálculo de score y `cumple_consigna`

```python
score = sum(caso.points for caso in casos_prueba if test_pasó)
max_score = sum(caso.points for caso in casos_prueba)

cumple_consigna = (
    compilation.success
    AND todos los checks estáticos pasaron
    AND todos los tests I/O pasaron
)
```

### 4.8 Feedback LLM (opcional)

Si existe `OPENAI_API_KEY` en el entorno, se llama a `analyzer.py` que usa LangChain + OpenAI para generar un comentario narrativo sobre la entrega. Se guarda en `submission.feedback_llm`. Si no hay API key o falla → `null`.

### 4.9 Persistencia

Se guardan en SQLite:
- Un registro `Submission` con `status="completed"`, `score`, `max_score`, `feedback_llm`, y un JSON con compilación + checks
- Un `TestResult` por cada `CasoPrueba`, con `passed`, `points_obtained`, `stdout`, `stderr`, `actual_output`, `execution_time_ms`

### 4.10 Respuesta al frontend

El endpoint devuelve `SubmissionOut` con toda la información: compilación, checks estáticos, tests I/O con detalle (input usado, output esperado, output obtenido), score, feedback LLM.

El frontend muestra en `FeedbackView`:
- Badge "Cumple / No cumple la consigna"
- Score con porcentaje
- Warnings de compilación
- Tabla de checks estáticos
- Detalle de cada test: si falló, muestra input, output esperado y output obtenido
- Feedback LLM (si existe)

---

## 5. Base de datos

SQLite en `service/corrector.db`. Se crea automáticamente al arrancar la app (`Base.metadata.create_all`).

### Tablas y relaciones

```
Consigna  (id, nombre, descripcion, is_active, requires_tda, requires_void_pointer,
           requires_modularization, created_at)
    │
    ├──< CasoPrueba  (id, consigna_id, descripcion, input, expected_output,
    │                 check_type, timeout_seg, points, visibility)
    │
    ├──< CheckEstatico  (id, consigna_id, descripcion, pattern, check_type, min_count)
    │
    └──< Submission  (id, student_name, consigna_id, original_filename, status,
                      score, max_score, feedback_llm, result_json, created_at)
              │
              └──< TestResult  (id, submission_id, test_case_id, passed,
                                points_obtained, stdout, stderr, expected_output,
                                actual_output, execution_time_ms, error_message)
```

**Cascade delete**: al borrar una `Consigna` se borran automáticamente sus `CasoPrueba`, `CheckEstatico` y `Submission` (incluyendo sus `TestResult`).

El campo `result_json` en `Submission` es un JSON embebido con `compilacion` y `checks_estaticos` — estos datos no se normalizan en tablas propias para simplificar la reconstrucción de la respuesta.

---

## 6. Qué hace seed.py

`seed.py` es un script standalone que carga la consigna de ejemplo "TP2 - Pila y Cola void" con datos reales del curso:

**Checks estáticos que carga:**
1. Uso de `void*` (punteros genéricos)
2. Uso de callbacks (puntero a función en firma)
3. Al menos 3 `typedef struct` (3 TDAs mínimos)

**Casos de prueba que carga (11 pts total):**
1. El programa termina limpiamente con opción 0 (exitcode, 1 pt)
2. Apilar un elemento y verlo en el tope (contains "Juan", 2 pts)
3. LIFO: el último apilado aparece primero (contains "Pedro", 2 pts)
4. Encolar un elemento y verlo al frente (contains "Juan", 2 pts)
5. FIFO: el primero encolado aparece primero (contains "Juan", 2 pts)
6. Desapilar con pila vacía no crashea (exitcode, 1 pt)
7. Desencolar con cola vacía no crashea (exitcode, 1 pt)

Si ya existe la consigna, la borra y la recrea (idempotente). Correr con:
```bash
cd service
poetry run python seed.py
```

---

## 7. Qué hacen los tests funcionales

### `tests/functional/test_api.py` (19 tests)

Prueba el endpoint legacy `POST /api/analizar`. Crea una DB SQLite temporal por test (no persiste entre tests). Verifica:
- Rechazo de archivos no-ZIP (400)
- Consigna inexistente (404)
- ZIP corrupto (400)
- Path traversal (400)
- Flujo exitoso con compilación ok
- Compilación con warnings sigue siendo exitosa
- Checks estáticos reales (sin mock) con código que tiene/no tiene `malloc`
- Tests I/O mockeados que pasan/fallan
- Estructura completa de la respuesta

### `tests/functional/test_submissions.py` (19 tests)

Prueba los endpoints nuevos `POST /api/submissions/analyze` y `GET /api/submissions/{id}`. Misma estructura que `test_api.py` pero verifica además:
- Persistencia: el GET devuelve los mismos datos que el POST
- Score parcial (dos tests, uno pasa y uno falla)
- `points_obtained` es 0 cuando el test falla
- `error_message` se guarda correctamente
- `cumple_consigna` combina correctamente checks y tests

---

## 8. Qué está mockeado y qué corre real

### En los tests

| Componente | Estado en tests unitarios | Estado en tests funcionales |
|---|---|---|
| `zip_validator` (extracción) | Real | Real |
| `static_analyzer` (regex) | Real | Real |
| `compiler` (Docker GCC) | Mock de `subprocess.run` | Mock de `compile_c_files` |
| `test_runner` (Docker run) | Mock de `subprocess.run` | Mock de `run_tests` |
| Base de datos | — | SQLite temporal en `tmp_path` |

### En producción (`poetry run uvicorn ...`)

| Componente | Estado |
|---|---|
| `zip_validator` | Real |
| `static_analyzer` | Real (regex en Python) |
| `compiler` | Real — requiere Docker instalado |
| `test_runner` | Real — requiere Docker instalado y la imagen `gcc:latest` |
| LLM feedback | Real si `OPENAI_API_KEY` está en `.env` |

**Importante:** Si Docker no está corriendo, los endpoints de análisis fallan con `FileNotFoundError` o `subprocess.CalledProcessError`.

---

## 9. Qué falta para el MVP

| Prioridad | Feature | Estado |
|---|---|---|
| Alta | Admin UI para crear consignas | ✅ Implementado hoy |
| Alta | Autenticación básica para el admin | ❌ Pendiente |
| Media | Migrar `on_event("startup")` a `lifespan` | ❌ Deprecation warning menor |
| Media | Parser GCC con `-fdiagnostics-format=json` | ❌ Hoy es regex sobre stderr |
| Media | Corrección masiva (subir N entregas de una vez) | ❌ Hoy es de a una |
| Baja | Historial de submissions por alumno/consigna | ❌ No hay listado de submissions |
| Baja | Integración con campus/aula virtual de UNLa | ❌ Requiere trabajo con infraestructura de la facultad |

---

## 10. Próximos pasos recomendados para mañana

**Opción A — Autenticación básica (seguridad mínima):**
Agregar una clave API fija o usuario/contraseña para proteger los endpoints `/api/admin/*`. Con FastAPI es ~30 líneas usando `HTTPBasic` o un header `X-Admin-Key`. Sin esto, cualquier persona con acceso a la red puede modificar consignas.

**Opción B — Historial de submissions:**
`GET /api/submissions?consigna_id=X` para que el profesor pueda ver todas las entregas de una consigna. Requiere solo un endpoint nuevo y una tabla en la Admin UI.

**Opción C — Migración `on_event` a `lifespan`:**
Cambio de 10 líneas en `main.py`. Elimina el deprecation warning de FastAPI. Bajo riesgo, alto valor de mantenimiento.

**Recomendación:** Empezar por **A** (autenticación básica) porque la Admin UI recién agregada está completamente expuesta, luego **B** porque es lo que convierte el sistema en una herramienta de seguimiento y no solo un corrector de una sola vez.

---

## 11. Comandos para levantar el proyecto

### Backend (FastAPI — puerto 8000)
```bash
cd service
poetry install          # solo la primera vez o cuando cambien dependencias
poetry run uvicorn app.main:app --reload
```

### Frontend (React/Vite — puerto 5173)
```bash
cd frontend
npm install             # solo la primera vez
npm run dev
```

### Cargar datos de ejemplo
```bash
cd service
poetry run python seed.py
```

### Correr tests
```bash
cd service

# Toda la suite principal (unit + functional + property)
poetry run pytest

# Verbose con traceback corto
poetry run pytest -v --tb=short

# Solo tests unitarios (rápido, sin Docker)
poetry run pytest tests/unit/

# Solo tests funcionales
poetry run pytest tests/functional/

# Solo property tests (Hypothesis)
poetry run pytest tests/property/

# Tests de memoria Valgrind (requieren Docker)
poetry run pytest tests/memory/ -v

# Tests de performance (requieren benchmark)
poetry run pytest tests/performance/ -v

# Un test específico
poetry run pytest tests/unit/test_compiler.py::test_compilacion_exitosa
```

### Lint frontend
```bash
cd frontend
npm run lint
```

---

## 12. Riesgos y decisiones pendientes

### Seguridad
- **Sin autenticación en el admin**: cualquiera que llegue al puerto 8000 puede crear, editar o borrar consignas. Para un entorno de red universitaria interna es tolerable a corto plazo, pero debe resolverse antes de exponer a internet.
- **Docker como único límite de sandboxing**: si Docker no está configurado con límites del kernel (cgroups v2), `--pids-limit` puede no funcionar en algunas distros. Testeado en Windows con Docker Desktop.

### Arquitectura
- **`result_json` como campo blob**: la compilación y los checks estáticos se guardan como JSON dentro de un campo Text, no como tablas normalizadas. Funciona para el MVP pero dificulta queries del tipo "¿cuántos alumnos fallaron el check X?".
- **`on_event("startup")` deprecado**: FastAPI >= 0.93 usa `lifespan` en su lugar. El código actual funciona pero genera un warning en la consola.

### Producto
- **El parser GCC es regex sobre stderr**: funciona para errores simples. Para errores multi-línea (como los de templates en C++) puede perder contexto. El PDF del framework recomienda `-fdiagnostics-format=json`.
- **Corrección de a uno**: hoy el sistema recibe un ZIP por vez. Si la facultad quiere hacer corrección masiva al cierre del TP, necesitaría un endpoint batch o integración con el campus.

---

## 13. Contexto conceptual hablado

### Este proyecto no es LeetCode

LeetCode y los jueces online corrigen funciones o programas de un solo archivo con entrada/salida estándar bien definida. Este proyecto corrige **trabajos prácticos modulares en C** que:
- Tienen múltiples archivos `.c` y `.h` (TDAs, módulos separados)
- Requieren verificar que el alumno usó ciertas estructuras de datos propias (no `std::stack`)
- Necesitan comprobar que el código respeta el paradigma TDA (encapsulamiento, punteros void como genéricos, callbacks)
- El programa interactúa con el usuario por un menú de consola, no recibe entrada única

Por eso el sistema combina dos tipos de checks:
1. **Checks estáticos** (regex sobre código fuente): detectan si el alumno usó las construcciones requeridas
2. **Tests I/O** (ejecutar el binario con inputs de menú): verifican comportamiento real

### Docker es obligatorio para ejecutar código del alumno

El código C del alumno es código desconocido y potencialmente malicioso (intencionalmente o no). Sin sandboxing, un `fork bomb`, un `while(1)` o un `rm -rf` en el código podría tumbar el servidor. Docker con los flags:
```
--memory=128m --cpus=0.5 --pids-limit=128 --network=none
--read-only --tmpfs /tmp:size=64m --cap-drop=ALL
--security-opt=no-new-privileges --user=1000:1000
```
limita memoria, CPU, procesos, red, filesystem y privilegios. `--pids-limit=128` es el más crítico: impide fork bombs.

### El LLM solo da feedback narrativo, no pone nota

La nota la pone el sistema determinístico (checks + tests I/O con puntaje por caso). El LLM (hoy OpenAI GPT-4o-mini, planificado Ollama local) genera un comentario en lenguaje natural para el profesor sobre la calidad del código. No interviene en `cumple_consigna` ni en `score`. Esto es una decisión deliberada: el LLM puede alucinar; la nota no puede depender de eso.

### La app hoy la usa el profesor, a futuro los alumnos en masa

El flujo actual está pensado para que el **profesor use la app directamente**: sube el ZIP de un alumno, ve el resultado. A futuro la idea es integrarse con el campus virtual o la app de la facultad (Moodle, SIU, o similar) para que el alumno suba su ZIP desde allí y el corrector procese las entregas automáticamente al vencimiento del TP. Eso requiere:
- Un endpoint batch o webhook
- Autenticación integrada con el sistema de la facultad
- Almacenamiento de submissions con historial por alumno y por TP
