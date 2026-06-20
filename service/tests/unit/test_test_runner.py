"""
Tests unitarios de test_runner.py.
subprocess.run se mockea siempre: el primer call es la compilación,
los siguientes son la ejecución de cada test case.
"""
import subprocess
from unittest.mock import patch, MagicMock, call
import pytest
from app.services.test_runner import run_tests
from app.models.models import CasoPrueba


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_caso(
    descripcion: str = "test",
    input: str = "",
    expected_output: str = "",
    check_type: str = "contains",
    timeout_seg: int = 5,
) -> MagicMock:
    c = MagicMock(spec=CasoPrueba)
    c.descripcion = descripcion
    c.input = input
    c.expected_output = expected_output
    c.check_type = check_type
    c.timeout_seg = timeout_seg
    return c


def _run(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def _compile_ok() -> MagicMock:
    return _run(returncode=0)


def _compile_fail() -> MagicMock:
    return _run(returncode=1, stderr="error: undeclared identifier")


# ---------------------------------------------------------------------------
# Sin archivos .c
# ---------------------------------------------------------------------------

def test_sin_archivos_c_todos_fallan():
    casos = [make_caso("caso 1"), make_caso("caso 2")]
    results = run_tests([], casos)
    assert len(results) == 2
    assert all(not r["passed"] for r in results)
    assert all("No se encontraron" in r["error"] for r in results)


def test_solo_headers_sin_c_todos_fallan(tmp_path):
    h = tmp_path / "utils.h"
    h.write_text("void f();")
    casos = [make_caso()]
    results = run_tests([str(h)], casos)
    assert results[0]["passed"] is False
    assert "No se encontraron" in results[0]["error"]


def test_sin_test_cases_retorna_lista_vacia(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 0;}")
    with patch("app.services.test_runner.subprocess.run", return_value=_compile_ok()):
        results = run_tests([str(f)], [])
    assert results == []


# ---------------------------------------------------------------------------
# Compilación fallida
# ---------------------------------------------------------------------------

def test_compilacion_fallida_todos_los_casos_reportan_error(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){ return")
    casos = [make_caso("c1"), make_caso("c2"), make_caso("c3")]
    with patch("app.services.test_runner.subprocess.run", return_value=_compile_fail()):
        results = run_tests([str(f)], casos)
    assert len(results) == 3
    assert all(not r["passed"] for r in results)
    assert all("no compiló" in r["error"] or "compiló" in r["error"] for r in results)


def test_compilacion_fallida_no_ejecuta_casos(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){ return")
    casos = [make_caso()]
    with patch("app.services.test_runner.subprocess.run", return_value=_compile_fail()) as mock:
        run_tests([str(f)], casos)
    # Solo se llama una vez (compilación), nunca se ejecuta el binario
    assert mock.call_count == 1


# ---------------------------------------------------------------------------
# check_type = "contains"
# ---------------------------------------------------------------------------

def test_contains_stdout_contiene_expected(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 0;}")
    caso = make_caso(expected_output="Hola", check_type="contains")
    with patch("app.services.test_runner.subprocess.run", side_effect=[
        _compile_ok(),
        _run(stdout="Hola mundo\n"),
    ]):
        results = run_tests([str(f)], [caso])
    assert results[0]["passed"] is True


def test_contains_case_insensitive(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 0;}")
    caso = make_caso(expected_output="hola", check_type="contains")
    with patch("app.services.test_runner.subprocess.run", side_effect=[
        _compile_ok(),
        _run(stdout="HOLA MUNDO\n"),
    ]):
        results = run_tests([str(f)], [caso])
    assert results[0]["passed"] is True


def test_contains_stdout_no_contiene_expected(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 0;}")
    caso = make_caso(expected_output="Chau", check_type="contains")
    with patch("app.services.test_runner.subprocess.run", side_effect=[
        _compile_ok(),
        _run(stdout="Hola mundo\n"),
    ]):
        results = run_tests([str(f)], [caso])
    assert results[0]["passed"] is False


# ---------------------------------------------------------------------------
# check_type = "exact"
# ---------------------------------------------------------------------------

def test_exact_stdout_coincide_exactamente(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 0;}")
    caso = make_caso(expected_output="42", check_type="exact")
    with patch("app.services.test_runner.subprocess.run", side_effect=[
        _compile_ok(),
        _run(stdout="42\n"),
    ]):
        results = run_tests([str(f)], [caso])
    assert results[0]["passed"] is True


def test_exact_ignora_whitespace_borde(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 0;}")
    caso = make_caso(expected_output="  42  ", check_type="exact")
    with patch("app.services.test_runner.subprocess.run", side_effect=[
        _compile_ok(),
        _run(stdout="42\n"),
    ]):
        results = run_tests([str(f)], [caso])
    assert results[0]["passed"] is True


def test_exact_stdout_diferente_falla(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 0;}")
    caso = make_caso(expected_output="42", check_type="exact")
    with patch("app.services.test_runner.subprocess.run", side_effect=[
        _compile_ok(),
        _run(stdout="43\n"),
    ]):
        results = run_tests([str(f)], [caso])
    assert results[0]["passed"] is False


# ---------------------------------------------------------------------------
# check_type = "exitcode"
# ---------------------------------------------------------------------------

def test_exitcode_cero_pasa(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 0;}")
    caso = make_caso(check_type="exitcode")
    with patch("app.services.test_runner.subprocess.run", side_effect=[
        _compile_ok(),
        _run(returncode=0),
    ]):
        results = run_tests([str(f)], [caso])
    assert results[0]["passed"] is True


def test_exitcode_distinto_de_cero_falla(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 1;}")
    caso = make_caso(check_type="exitcode")
    with patch("app.services.test_runner.subprocess.run", side_effect=[
        _compile_ok(),
        _run(returncode=1),
    ]):
        results = run_tests([str(f)], [caso])
    assert results[0]["passed"] is False


def test_check_type_desconocido_falla(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 0;}")
    caso = make_caso(check_type="regex_magico")
    with patch("app.services.test_runner.subprocess.run", side_effect=[
        _compile_ok(),
        _run(stdout="cualquier cosa"),
    ]):
        results = run_tests([str(f)], [caso])
    assert results[0]["passed"] is False


# ---------------------------------------------------------------------------
# Múltiples casos de prueba
# ---------------------------------------------------------------------------

def test_multiples_casos_independientes(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 0;}")
    casos = [
        make_caso("pasa", expected_output="ok", check_type="contains"),
        make_caso("falla", expected_output="no está", check_type="contains"),
        make_caso("pasa exitcode", check_type="exitcode"),
    ]
    with patch("app.services.test_runner.subprocess.run", side_effect=[
        _compile_ok(),
        _run(stdout="ok output"),
        _run(stdout="otra cosa"),
        _run(returncode=0),
    ]):
        results = run_tests([str(f)], casos)
    assert len(results) == 3
    assert results[0]["passed"] is True
    assert results[1]["passed"] is False
    assert results[2]["passed"] is True


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------

def test_timeout_en_ejecucion_reporta_error(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 0;}")
    caso = make_caso("loop infinito", timeout_seg=3)
    with patch("app.services.test_runner.subprocess.run", side_effect=[
        _compile_ok(),
        subprocess.TimeoutExpired("docker", 3),
    ]):
        results = run_tests([str(f)], [caso])
    assert results[0]["passed"] is False
    assert "Timeout" in results[0]["error"]
    assert "3" in results[0]["error"]


def test_timeout_en_un_caso_no_afecta_al_siguiente(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 0;}")
    casos = [make_caso("timeout"), make_caso("ok", expected_output="bien", check_type="contains")]
    with patch("app.services.test_runner.subprocess.run", side_effect=[
        _compile_ok(),
        subprocess.TimeoutExpired("docker", 5),
        _run(stdout="bien"),
    ]):
        results = run_tests([str(f)], casos)
    assert results[0]["passed"] is False
    assert results[1]["passed"] is True


# ---------------------------------------------------------------------------
# Output y stderr truncados
# ---------------------------------------------------------------------------

def test_output_truncado_a_500_chars(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 0;}")
    caso = make_caso(expected_output="x", check_type="contains")
    stdout_largo = "x" * 1000
    with patch("app.services.test_runner.subprocess.run", side_effect=[
        _compile_ok(),
        _run(stdout=stdout_largo),
    ]):
        results = run_tests([str(f)], [caso])
    assert len(results[0]["output"]) == 500


def test_stderr_truncado_a_200_chars(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 0;}")
    caso = make_caso(check_type="exitcode")
    with patch("app.services.test_runner.subprocess.run", side_effect=[
        _compile_ok(),
        _run(returncode=1, stderr="e" * 500),
    ]):
        results = run_tests([str(f)], [caso])
    assert len(results[0]["error"]) == 200


def test_stderr_vacio_retorna_string_vacio(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 0;}")
    caso = make_caso(check_type="exitcode")
    with patch("app.services.test_runner.subprocess.run", side_effect=[
        _compile_ok(),
        _run(returncode=0, stderr=""),
    ]):
        results = run_tests([str(f)], [caso])
    assert results[0]["error"] == ""


# ---------------------------------------------------------------------------
# Flags de seguridad Docker
# ---------------------------------------------------------------------------

def test_ejecucion_incluye_flags_de_seguridad(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 0;}")
    caso = make_caso(check_type="exitcode")
    with patch("app.services.test_runner.subprocess.run", side_effect=[
        _compile_ok(),
        _run(returncode=0),
    ]) as mock:
        run_tests([str(f)], [caso])
    # El segundo call es la ejecución del binario
    run_cmd = " ".join(mock.call_args_list[1][0][0])
    assert "--pids-limit=128" in run_cmd
    assert "--network=none" in run_cmd
    assert "--cap-drop=ALL" in run_cmd
    assert "--security-opt=no-new-privileges" in run_cmd
    assert "--user=1000:1000" in run_cmd
