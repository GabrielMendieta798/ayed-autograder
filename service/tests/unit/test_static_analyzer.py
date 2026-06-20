import os
import pytest
from unittest.mock import MagicMock
from app.services.static_analyzer import run_static_checks
from app.models.models import CheckEstatico


def make_check(descripcion: str, pattern: str, check_type: str = "exists", min_count: int = 1) -> CheckEstatico:
    c = MagicMock(spec=CheckEstatico)
    c.descripcion = descripcion
    c.pattern = pattern
    c.check_type = check_type
    c.min_count = min_count
    return c


def write_c_file(tmp_path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# check_type = "exists"
# ---------------------------------------------------------------------------

def test_exists_patron_presente(tmp_path):
    f = write_c_file(tmp_path, "main.c", "void* ptr = NULL;\nDatoPtr x;")
    check = make_check("Usa puntero void", r"void\s*\*")
    results = run_static_checks([f], [check])
    assert results[0]["passed"] is True
    assert results[0]["found"] >= 1


def test_exists_patron_ausente(tmp_path):
    f = write_c_file(tmp_path, "main.c", "int main() { return 0; }")
    check = make_check("Usa malloc", r"\bmalloc\b")
    results = run_static_checks([f], [check])
    assert results[0]["passed"] is False
    assert results[0]["found"] == 0


def test_exists_typedef_cuenta_como_presente(tmp_path):
    f = write_c_file(tmp_path, "main.c", "typedef void* DatoPtr;\nDatoPtr x = NULL;")
    check = make_check("Usa void*", r"void\s*\*")
    results = run_static_checks([f], [check])
    assert results[0]["passed"] is True


# ---------------------------------------------------------------------------
# check_type = "count_gte"
# ---------------------------------------------------------------------------

def test_count_gte_exactamente_minimo(tmp_path):
    f = write_c_file(tmp_path, "main.c", "malloc(1);\nmalloc(2);\nmalloc(3);")
    check = make_check("Al menos 3 malloc", r"\bmalloc\b", check_type="count_gte", min_count=3)
    results = run_static_checks([f], [check])
    assert results[0]["passed"] is True


def test_count_gte_por_debajo_del_minimo(tmp_path):
    f = write_c_file(tmp_path, "main.c", "malloc(1);\nmalloc(2);")
    check = make_check("Al menos 3 malloc", r"\bmalloc\b", check_type="count_gte", min_count=3)
    results = run_static_checks([f], [check])
    assert results[0]["passed"] is False


def test_count_gte_supera_el_minimo(tmp_path):
    f = write_c_file(tmp_path, "main.c", "\n".join(f"free(p{i});" for i in range(10)))
    check = make_check("Al menos 3 free", r"\bfree\b", check_type="count_gte", min_count=3)
    results = run_static_checks([f], [check])
    assert results[0]["passed"] is True
    assert results[0]["found"] == 10


# ---------------------------------------------------------------------------
# Múltiples archivos y checks
# ---------------------------------------------------------------------------

def test_multiple_files_se_concatenan(tmp_path):
    f1 = write_c_file(tmp_path, "a.c", "malloc(1);")
    f2 = write_c_file(tmp_path, "b.c", "malloc(2);")
    check = make_check("Al menos 2 malloc", r"\bmalloc\b", check_type="count_gte", min_count=2)
    results = run_static_checks([f1, f2], [check])
    assert results[0]["passed"] is True


def test_multiple_checks_retorna_todos(tmp_path):
    f = write_c_file(tmp_path, "main.c", "malloc(1);\nfree(p);")
    checks = [
        make_check("Usa malloc", r"\bmalloc\b"),
        make_check("Usa free", r"\bfree\b"),
        make_check("Usa printf", r"\bprintf\b"),
    ]
    results = run_static_checks([f], checks)
    assert len(results) == 3
    assert results[0]["passed"] is True
    assert results[1]["passed"] is True
    assert results[2]["passed"] is False


def test_sin_archivos_retorna_lista_vacia():
    results = run_static_checks([], [make_check("X", r"x")])
    assert results[0]["passed"] is False
    assert results[0]["found"] == 0


def test_check_type_desconocido_retorna_false(tmp_path):
    f = write_c_file(tmp_path, "main.c", "malloc(1);")
    check = make_check("X", r"\bmalloc\b", check_type="inexistente")
    results = run_static_checks([f], [check])
    assert results[0]["passed"] is False


def test_sin_checks_retorna_lista_vacia(tmp_path):
    f = write_c_file(tmp_path, "main.c", "int main(){return 0;}")
    results = run_static_checks([f], [])
    assert results == []
