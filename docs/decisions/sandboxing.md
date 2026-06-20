# ADR: Sandboxing de compilación y ejecución de C con Docker

**Fecha:** 2026-05-06  
**Estado:** Aceptado

## Contexto

El backend compila y ejecuta código C enviado por alumnos. Antes de este cambio, `compiler.py` y `test_runner.py` invocaban `gcc` y el binario resultante directamente como subprocesos del host, sin ningún aislamiento. Cualquier alumno podía enviar código que leyera el sistema de archivos del servidor, abriera conexiones de red, o consumiera recursos arbitrarios.

## Decisión

Toda compilación y ejecución de código de alumnos ocurre dentro de un contenedor Docker efímero (`gcc:latest`) con los siguientes límites:

| Flag | Valor | Razón |
|---|---|---|
| `--memory` | 128 MB | Evita que un programa con leak o loop infinito en memoria afecte al host |
| `--cpus` | 0.5 | Limita CPU para que un loop infinito no sature el servidor |
| `--network=none` | — | Impide que el código compilado abra conexiones salientes |
| `--read-only` | — | El filesystem del contenedor es de solo lectura |
| `--tmpfs /tmp` | 64 MB | Único espacio escribible; el binario compilado vive ahí |
| `-v workdir:/code:ro` | — | Los fuentes se montan en modo lectura |
| `timeout` subprocess | 30s compilación, `timeout_seg + 5s` ejecución | Mata el contenedor si Docker mismo cuelga |

El directorio temporal del host se crea con `tempfile.mkdtemp()` y se elimina en el bloque `finally`, independientemente del resultado.

## Consecuencias

**Positivas**
- El código de alumnos no puede afectar al proceso Python del servidor ni al sistema de archivos del host.
- El aislamiento de red elimina la clase de ataques de exfiltración o callback.
- Los contenedores son efímeros (`--rm`); no acumulan estado entre correcciones.

**Negativas / limitaciones**
- Docker debe estar instalado y accesible en el host donde corre el backend. Si no está disponible, la API retorna un error 500 claro.
- La imagen `gcc:latest` se descarga en el primer uso (~1.2 GB). En producción conviene tenerla pre-pulled en el deploy.
- Hay overhead de startup del contenedor (~0.5–1s por request). Aceptable para un corrector que no necesita baja latencia.
- No hay límite de procesos (`--pids-limit`); se puede agregar si se detecta abuso con `fork bombs`.
