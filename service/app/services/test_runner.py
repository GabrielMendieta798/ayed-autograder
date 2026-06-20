import subprocess
import os
import shutil
import tempfile
from app.models.models import CasoPrueba

DOCKER_IMAGE = "gcc:latest"
COMPILE_TIMEOUT = 30


def run_tests(source_files: list[str], test_cases: list[CasoPrueba]) -> list[dict]:
    c_files = [f for f in source_files if f.endswith(".c")]

    if not c_files:
        return [{
            "descripcion": caso.descripcion,
            "passed": False,
            "output": "",
            "error": "No se encontraron archivos .c",
        } for caso in test_cases]

    workdir = tempfile.mkdtemp()
    try:
        for path in c_files:
            shutil.copy2(path, os.path.join(workdir, os.path.basename(path)))

        basenames = [os.path.basename(f) for f in c_files]

        compile_result = subprocess.run(
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
                "-v", f"{workdir}:/code",  # rw: gcc escribe el binario en el host
                "-w", "/code",
                DOCKER_IMAGE,
                "gcc", "-std=c11", "-Wall", "-o", "/code/out",
            ] + basenames,
            capture_output=True,
            text=True,
            timeout=COMPILE_TIMEOUT,
        )

        if compile_result.returncode != 0:
            gcc_stderr = compile_result.stderr[:500] if compile_result.stderr else "El código no compiló"
            return [{
                "descripcion": caso.descripcion,
                "passed": False,
                "output": "",
                "error": gcc_stderr,
            } for caso in test_cases]

        results = []
        for caso in test_cases:
            try:
                run = subprocess.run(
                    [
                        "docker", "run", "--rm", "-i",
                        "--memory=128m",
                        "--cpus=0.5",
                        "--pids-limit=128",
                        "--network=none",
                        "--read-only",
                        "--tmpfs", "/tmp:size=64m",
                        "--cap-drop=ALL",
                        "--security-opt=no-new-privileges",
                        "--user=1000:1000",
                        "-v", f"{workdir}:/code:ro",  # ro: el código corre sin poder escribir fuentes
                        DOCKER_IMAGE,
                        "/code/out",
                    ],
                    input=caso.input,
                    capture_output=True,
                    text=True,
                    timeout=caso.timeout_seg + 5,
                )
                stdout = run.stdout

                if caso.check_type == "exitcode":
                    passed = run.returncode == 0
                elif caso.check_type == "contains":
                    passed = caso.expected_output.lower() in stdout.lower()
                elif caso.check_type == "exact":
                    passed = stdout.strip() == caso.expected_output.strip()
                else:
                    passed = False

                results.append({
                    "descripcion": caso.descripcion,
                    "passed": passed,
                    "output": stdout[:500],
                    "error": run.stderr[:200] if run.stderr else "",
                })

            except subprocess.TimeoutExpired:
                results.append({
                    "descripcion": caso.descripcion,
                    "passed": False,
                    "output": "",
                    "error": f"Timeout ({caso.timeout_seg}s)",
                })

        return results

    finally:
        shutil.rmtree(workdir, ignore_errors=True)
