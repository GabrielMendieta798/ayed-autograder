"""
Tests de performance — miden tiempo real de ejecución sin Docker.
Correr con: poetry run pytest tests/performance/ -v
Comparar runs: poetry run pytest tests/performance/ --benchmark-compare
"""
import io
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass

import pytest

from app.services.zip_validator import validate_and_extract
from app.services.static_analyzer import run_static_checks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_zip_bytes(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def _write_zip(tmp_path, files: dict[str, str], filename="entrega.zip") -> str:
    path = str(tmp_path / filename)
    with open(path, "wb") as f:
        f.write(_make_zip_bytes(files))
    return path


def _write_source_files(tmp_path, files: dict[str, str]) -> list[str]:
    paths = []
    for name, content in files.items():
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        paths.append(str(p))
    return paths


@dataclass
class FakeCheck:
    pattern: str
    check_type: str = "exists"
    min_count: int = 1
    descripcion: str = "check"


C_SMALL = "#include <stdio.h>\nint main() { printf(\"hola\"); return 0; }\n"
C_MEDIUM = C_SMALL * 500     # ~50 KB por archivo
C_LARGE = C_SMALL * 5000     # ~500 KB por archivo


# ---------------------------------------------------------------------------
# validate_and_extract
# ---------------------------------------------------------------------------

class TestZipValidatorPerformance:
    """
    Cada benchmark crea un destino temporal fresco por iteración para que
    validate_and_extract siempre encuentre el directorio vacío.
    """

    def test_zip_1_archivo_pequeno(self, benchmark, tmp_path):
        """1 archivo .c de ~1 KB."""
        zip_path = _write_zip(tmp_path, {"main.c": C_SMALL})

        def run():
            dest = tempfile.mkdtemp()
            try:
                return validate_and_extract(zip_path, dest)
            finally:
                shutil.rmtree(dest, ignore_errors=True)

        result = benchmark(run)
        assert len(result) == 1

    def test_zip_10_archivos_medianos(self, benchmark, tmp_path):
        """10 archivos .c de ~50 KB cada uno (~500 KB total)."""
        files = {f"archivo{i:02d}.c": C_MEDIUM for i in range(10)}
        zip_path = _write_zip(tmp_path, files)

        def run():
            dest = tempfile.mkdtemp()
            try:
                return validate_and_extract(zip_path, dest)
            finally:
                shutil.rmtree(dest, ignore_errors=True)

        result = benchmark(run)
        assert len(result) == 10

    def test_zip_50_archivos_pequenos(self, benchmark, tmp_path):
        """50 archivos .c de ~1 KB (límite de cantidad del sistema)."""
        files = {f"f{i:02d}.c": C_SMALL for i in range(50)}
        zip_path = _write_zip(tmp_path, files)

        def run():
            dest = tempfile.mkdtemp()
            try:
                return validate_and_extract(zip_path, dest)
            finally:
                shutil.rmtree(dest, ignore_errors=True)

        result = benchmark(run)
        assert len(result) == 50

    def test_zip_5_archivos_grandes(self, benchmark, tmp_path):
        """5 archivos .c de ~500 KB cada uno (~2.5 MB total)."""
        files = {f"grande{i}.c": C_LARGE for i in range(5)}
        zip_path = _write_zip(tmp_path, files)

        def run():
            dest = tempfile.mkdtemp()
            try:
                return validate_and_extract(zip_path, dest)
            finally:
                shutil.rmtree(dest, ignore_errors=True)

        result = benchmark(run)
        assert len(result) == 5

    def test_zip_archivos_mixtos(self, benchmark, tmp_path):
        """ZIP con .c, .h y archivos ignorados (.cbp, .txt)."""
        files = {
            "main.c": C_MEDIUM,
            "utils.c": C_MEDIUM,
            "utils.h": "#pragma once\nvoid f();\n",
            "proyecto.cbp": "<xml/>",
            "readme.txt": "ignorado",   # no se extrae
        }
        zip_path = _write_zip(tmp_path, files)

        def run():
            dest = tempfile.mkdtemp()
            try:
                return validate_and_extract(zip_path, dest)
            finally:
                shutil.rmtree(dest, ignore_errors=True)

        result = benchmark(run)
        # .txt se filtra; .c y .h se retornan
        assert len(result) == 3


# ---------------------------------------------------------------------------
# run_static_checks
# ---------------------------------------------------------------------------

class TestStaticAnalyzerPerformance:
    """
    run_static_checks es una operación de solo lectura: crea los archivos
    fuente una vez y los reutiliza en todas las iteraciones del benchmark.
    """

    def test_codigo_pequeno_pocos_checks(self, benchmark, tmp_path):
        """1 archivo ~1 KB, 3 checks simples."""
        paths = _write_source_files(tmp_path, {"main.c": C_SMALL})
        checks = [
            FakeCheck(pattern=r"#include\s*<stdio\.h>"),
            FakeCheck(pattern=r"\bmalloc\b", check_type="exists"),
            FakeCheck(pattern=r"\bprintf\b", check_type="count_gte", min_count=1),
        ]
        result = benchmark(run_static_checks, paths, checks)
        assert len(result) == 3

    def test_codigo_grande_pocos_checks(self, benchmark, tmp_path):
        """1 archivo ~500 KB, 3 checks — mide impacto del tamaño del código."""
        paths = _write_source_files(tmp_path, {"main.c": C_LARGE})
        checks = [
            FakeCheck(pattern=r"#include\s*<stdio\.h>"),
            FakeCheck(pattern=r"\bprintf\b", check_type="count_gte", min_count=1),
            FakeCheck(pattern=r"\bmalloc\b"),
        ]
        result = benchmark(run_static_checks, paths, checks)
        assert len(result) == 3

    def test_codigo_pequeno_muchos_checks(self, benchmark, tmp_path):
        """1 archivo ~1 KB, 20 checks — mide impacto de la cantidad de checks."""
        paths = _write_source_files(tmp_path, {"main.c": C_SMALL})
        checks = [
            FakeCheck(pattern=rf"\bvar{i}\b", descripcion=f"check {i}")
            for i in range(20)
        ]
        result = benchmark(run_static_checks, paths, checks)
        assert len(result) == 20

    def test_multiples_archivos(self, benchmark, tmp_path):
        """10 archivos medianos, 5 checks — mide impacto de múltiples fuentes."""
        files = {f"mod{i:02d}.c": C_MEDIUM for i in range(10)}
        paths = _write_source_files(tmp_path, files)
        checks = [
            FakeCheck(pattern=r"#include\s*<stdio\.h>"),
            FakeCheck(pattern=r"\bprintf\b", check_type="count_gte", min_count=5),
            FakeCheck(pattern=r"\bmain\b"),
            FakeCheck(pattern=r"\bfree\b"),
            FakeCheck(pattern=r"\bmalloc\b"),
        ]
        result = benchmark(run_static_checks, paths, checks)
        assert len(result) == 5

    def test_regex_complejo(self, benchmark, tmp_path):
        """Patrones regex complejos sobre código grande."""
        paths = _write_source_files(tmp_path, {"main.c": C_LARGE})
        checks = [
            FakeCheck(pattern=r"int\s+\w+\s*\([^)]*\)\s*\{"),   # definición de función
            FakeCheck(pattern=r"for\s*\([^;]*;[^;]*;[^)]*\)"),  # bucle for
            FakeCheck(pattern=r"(malloc|calloc|realloc)\s*\("),  # asignación heap
            FakeCheck(pattern=r"//[^\n]*|/\*[\s\S]*?\*/"),       # comentarios
        ]
        result = benchmark(run_static_checks, paths, checks)
        assert len(result) == 4
