"""
Tests unitarios de compiler.py.
Mockean subprocess.run para no necesitar Docker en la suite rápida.
"""
import subprocess
from unittest.mock import patch, MagicMock
import pytest
from app.services.compiler import compile_c_files


def _mock_run(returncode: int, stderr: str) -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stderr = stderr
    m.stdout = ""
    return m


# ---------------------------------------------------------------------------
# Compilación exitosa
# ---------------------------------------------------------------------------

def test_compilacion_exitosa(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 0;}")
    with patch("app.services.compiler.subprocess.run", return_value=_mock_run(0, "")) as mock:
        result = compile_c_files([str(f)])
    assert result.success is True
    assert result.errors == []
    assert result.warnings == []


def test_compilacion_exitosa_con_warnings(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){int x; return 0;}")
    stderr = "main.c:1:12: warning: unused variable 'x' [-Wunused-variable]"
    with patch("app.services.compiler.subprocess.run", return_value=_mock_run(0, stderr)):
        result = compile_c_files([str(f)])
    assert result.success is True
    assert result.errors == []
    assert len(result.warnings) == 1
    assert "warning:" in result.warnings[0]


def test_compilacion_multiples_archivos(tmp_path):
    f1 = tmp_path / "a.c"
    f2 = tmp_path / "b.c"
    f1.write_text("void f(){}")
    f2.write_text("int main(){return 0;}")
    with patch("app.services.compiler.subprocess.run", return_value=_mock_run(0, "")) as mock:
        result = compile_c_files([str(f1), str(f2)])
    assert result.success is True
    # Verifica que ambos basenames se pasan al comando docker
    cmd = mock.call_args[0][0]
    assert "a.c" in cmd
    assert "b.c" in cmd


# ---------------------------------------------------------------------------
# Compilación fallida
# ---------------------------------------------------------------------------

def test_compilacion_con_errores(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){ return")
    stderr = (
        "main.c:1:18: error: expected ';' before '}' token\n"
        "main.c:1:19: error: expected declaration or statement at end of input"
    )
    with patch("app.services.compiler.subprocess.run", return_value=_mock_run(1, stderr)):
        result = compile_c_files([str(f)])
    assert result.success is False
    assert len(result.errors) == 2
    assert all("error:" in e for e in result.errors)


def test_compilacion_con_errores_y_warnings(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){ int x; return")
    stderr = (
        "main.c:1:12: warning: unused variable 'x' [-Wunused-variable]\n"
        "main.c:1:25: error: expected ';' before '}' token"
    )
    with patch("app.services.compiler.subprocess.run", return_value=_mock_run(1, stderr)):
        result = compile_c_files([str(f)])
    assert result.success is False
    assert len(result.errors) == 1
    assert len(result.warnings) == 1


def test_stderr_sin_error_ni_warning_no_se_incluye(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 0;}")
    stderr = "In file included from main.c:1:\nnote: some diagnostic note"
    with patch("app.services.compiler.subprocess.run", return_value=_mock_run(0, stderr)):
        result = compile_c_files([str(f)])
    assert result.errors == []
    assert result.warnings == []


# ---------------------------------------------------------------------------
# Sin archivos .c
# ---------------------------------------------------------------------------

def test_sin_archivos_c_retorna_error():
    result = compile_c_files([])
    assert result.success is False
    assert any("No se encontraron" in e for e in result.errors)


def test_solo_headers_retorna_error(tmp_path):
    h = tmp_path / "utils.h"
    h.write_text("void f();")
    result = compile_c_files([str(h)])
    assert result.success is False
    assert any("No se encontraron" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Casos de fallo de infraestructura
# ---------------------------------------------------------------------------

def test_timeout_retorna_error(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 0;}")
    with patch("app.services.compiler.subprocess.run", side_effect=subprocess.TimeoutExpired("docker", 30)):
        result = compile_c_files([str(f)])
    assert result.success is False
    assert any("Timeout" in e or "timeout" in e for e in result.errors)


def test_docker_no_disponible_retorna_error(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 0;}")
    with patch("app.services.compiler.subprocess.run", side_effect=FileNotFoundError):
        result = compile_c_files([str(f)])
    assert result.success is False
    assert any("Docker" in e or "docker" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Estructura del comando Docker
# ---------------------------------------------------------------------------

def test_comando_incluye_flags_de_seguridad(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 0;}")
    with patch("app.services.compiler.subprocess.run", return_value=_mock_run(0, "")) as mock:
        compile_c_files([str(f)])
    cmd = mock.call_args[0][0]
    cmd_str = " ".join(cmd)
    assert "--network=none" in cmd_str
    assert "--memory" in cmd_str
    assert "--read-only" in cmd_str
    assert "--pids-limit=128" in cmd_str
    assert "--cap-drop=ALL" in cmd_str
    assert "--security-opt=no-new-privileges" in cmd_str
    assert "--user=1000:1000" in cmd_str


def test_comando_usa_std_c11(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 0;}")
    with patch("app.services.compiler.subprocess.run", return_value=_mock_run(0, "")) as mock:
        compile_c_files([str(f)])
    cmd = mock.call_args[0][0]
    assert "-std=c11" in cmd


def test_comando_incluye_wall_wextra(tmp_path):
    f = tmp_path / "main.c"
    f.write_text("int main(){return 0;}")
    with patch("app.services.compiler.subprocess.run", return_value=_mock_run(0, "")) as mock:
        compile_c_files([str(f)])
    cmd = mock.call_args[0][0]
    assert "-Wall" in cmd
    assert "-Wextra" in cmd
