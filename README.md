# Corrector Automático AED

Herramienta para que los profesores de la Universidad Nacional de Lanús corrijan automáticamente entregas de programación en C para la materia Algoritmos y Estructuras de Datos.

Los estudiantes suben un ZIP o RAR con sus archivos `.c`; el sistema los compila dentro de un sandbox Docker, ejecuta verificaciones estáticas del código y casos de prueba de entrada/salida, y devuelve un feedback detallado con puntaje.

> **Estado:** en desarrollo activo (Práctica Profesional Supervisada).

## Características

- Compilación en sandbox Docker aislado (sin red, sin fork bombs, memoria limitada)
- Checks estáticos configurables por consigna (regex sobre el código fuente)
- Casos de prueba I/O con stdin/stdout y tipos de verificación: `exitcode`, `contains`, `exact`
- API REST (FastAPI) + frontend React
- Admin UI para gestionar consignas, checks y casos de prueba

## Arquitectura

```
POST /api/analizar
  ├── zip_validator     → valida y extrae el ZIP/RAR de forma segura
  ├── compiler          → compila con GCC en Docker
  ├── static_analyzer   → ejecuta checks de código fuente
  └── test_runner       → corre casos de prueba en Docker
```

**Stack:** Python 3.12 · FastAPI · SQLAlchemy · SQLite/PostgreSQL · Docker · React · TypeScript · Vite

## Requisitos

- Python 3.12+ y [Poetry](https://python-poetry.org/)
- Node.js 18+
- Docker (para compilación y ejecución en sandbox)

## Inicio rápido

### Backend

```bash
cd service
cp .env.example .env          # completar variables si hace falta
poetry install
poetry run uvicorn app.main:app --reload
# API disponible en http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# UI disponible en http://localhost:5173
```

### Cargar datos de ejemplo

```bash
cd service
poetry run python ../demo-consigna-calculadora/seed_demo.py
```

Esto crea una consigna "TP Demo - Calculadora básica en C" con 5 casos de prueba para probar el flujo completo. Ver [`demo-consigna-calculadora/README.md`](demo-consigna-calculadora/README.md) para instrucciones detalladas.

## Tests

```bash
cd service
poetry run pytest                     # toda la suite
poetry run pytest tests/unit/         # unitarios (sin Docker)
poetry run pytest tests/functional/   # API con TestClient
poetry run pytest -v --tb=short       # verbose
```

## Variables de entorno

Copiar `service/.env.example` a `service/.env`:

| Variable | Default | Descripción |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./corrector.db` | URL de la base de datos |
| `OPENAI_API_KEY` | — | Opcional, para feedback LLM (no activo) |
| `OPENAI_MODEL` | `gpt-4o-mini` | Modelo a usar si se activa el LLM |

## Estructura del repositorio

```
corrector-automatico/
├── service/                  # Backend FastAPI
│   ├── app/
│   │   ├── api/              # Rutas
│   │   ├── models/           # Modelos SQLAlchemy + schemas Pydantic
│   │   ├── services/         # compiler, test_runner, static_analyzer, zip_validator
│   │   └── main.py
│   ├── tests/                # Unit, functional, property (Hypothesis)
│   └── seed.py               # Script para poblar la DB
├── frontend/                 # React + TypeScript + Vite
│   └── src/
│       ├── components/       # UploadForm, FeedbackView
│       └── App.tsx
├── demo-consigna-calculadora/ # Consigna de ejemplo con entregas de prueba
└── docs/                     # Bitácora y decisiones de arquitectura
```

## Seguridad del sandbox Docker

Cada compilación y ejecución corre en un contenedor efímero con:

```
--rm --memory=128m --cpus=0.5 --pids-limit=128 --network=none
--read-only --tmpfs /tmp:size=64m --cap-drop=ALL
--security-opt=no-new-privileges --user=1000:1000
```

`--pids-limit=128` es la flag más importante — previene fork bombs.

## Licencia

Uso académico — Universidad Nacional de Lanús.
