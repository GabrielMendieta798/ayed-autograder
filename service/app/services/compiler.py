import subprocess
import tempfile
import os
import shutil
from app.models.schemas import CompilationResult

DOCKER_IMAGE = "gcc:latest"
COMPILE_TIMEOUT = 30


def compile_c_files(source_files: list[str]) -> CompilationResult:
    c_files = [f for f in source_files if f.endswith(".c")]
    if not c_files:
        return CompilationResult(success=False, errors=["No se encontraron archivos .c"], warnings=[])

    workdir = tempfile.mkdtemp()
    try:
        for path in c_files:
            shutil.copy2(path, os.path.join(workdir, os.path.basename(path)))

        basenames = [os.path.basename(f) for f in c_files]

        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "--memory=128m",
                "--cpus=0.5",
                "--pids-limit=128",
                "--network=none",
                "--read-only",
                "--tmpfs", "/tmp:size=64m",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "--user=1000:1000",
                "-v", f"{workdir}:/code:ro",
                "-w", "/code",
                DOCKER_IMAGE,
                "gcc", "-std=c11", "-Wall", "-Wextra", "-o", "/tmp/out",
            ] + basenames,
            capture_output=True,
            text=True,
            timeout=COMPILE_TIMEOUT,
        )

        errors = []
        warnings = []
        for line in result.stderr.splitlines():
            if "error:" in line:
                errors.append(line.strip())
            elif "warning:" in line:
                warnings.append(line.strip())

        return CompilationResult(
            success=result.returncode == 0,
            errors=errors,
            warnings=warnings,
        )
    except subprocess.TimeoutExpired:
        return CompilationResult(success=False, errors=["Timeout: la compilación tardó demasiado"], warnings=[])
    except FileNotFoundError:
        return CompilationResult(success=False, errors=["Docker no está disponible en el servidor"], warnings=[])
    finally:
        shutil.rmtree(workdir, ignore_errors=True)