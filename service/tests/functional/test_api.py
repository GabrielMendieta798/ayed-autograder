"""
Tests funcionales de la API FastAPI.
Usan TestClient con una DB SQLite en memoria.
Solo mockean compile_c_files y run_tests (requieren Docker).
validate_and_extract y run_static_checks corren real contra ZIPs reales.
"""
import io
import zipfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from app.main import app
from app.models.database import Base, get_db
from app.models.models import Consigna, CheckEstatico, CasoPrueba
from app.models.schemas import CompilationResult


# ---------------------------------------------------------------------------
# Fixtures de DB y cliente
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_engine(tmp_path):
    url = f"sqlite:///{tmp_path}/test.db"
    engine = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def consigna_simple(db_session) -> Consigna:
    """Consigna sin checks ni tests — útil para probar el flujo básico."""
    c = Consigna(nombre="TP1 Básico", descripcion="Implementar hello world")
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


@pytest.fixture
def consigna_con_checks(db_session) -> Consigna:
    """Consigna con un check estático y un test I/O."""
    c = Consigna(nombre="TP2 Con checks", descripcion="Usar malloc y free")
    db_session.add(c)
    db_session.flush()
    db_session.add(CheckEstatico(
        consigna_id=c.id,
        descripcion="Usa malloc",
        pattern=r"\bmalloc\b",
        check_type="exists",
        min_count=1,
    ))
    db_session.add(CasoPrueba(
        consigna_id=c.id,
        descripcion="Imprime 42",
        input="",
        expected_output="42",
        check_type="contains",
        timeout_seg=5,
    ))
    db_session.commit()
    db_session.refresh(c)
    return c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def post_analizar(client, zip_bytes: bytes, consigna_id: int,
                  nombre: str = "Juan Perez", filename: str = "entrega.zip"):
    return client.post(
        "/api/analizar",
        files={"archivo": (filename, zip_bytes, "application/zip")},
        data={"consigna_id": str(consigna_id), "nombre_alumno": nombre},
    )


COMPILE_OK = CompilationResult(success=True, errors=[], warnings=[])
COMPILE_FAIL = CompilationResult(success=False, errors=["error: expected ';'"], warnings=[])

HELLO_C = '#include <stdio.h>\nint main(){printf("42\\n");return 0;}'
MALLOC_C = '#include <stdlib.h>\nint main(){int*p=malloc(4);free(p);return 0;}'


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /api/consignas
# ---------------------------------------------------------------------------

def test_listar_consignas_vacio(client):
    r = client.get("/api/consignas")
    assert r.status_code == 200
    assert r.json() == []


def test_listar_consignas_retorna_las_existentes(client, consigna_simple):
    r = client.get("/api/consignas")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["nombre"] == "TP1 Básico"
    assert "id" in data[0]


def test_listar_consignas_multiples(client, db_session):
    db_session.add_all([
        Consigna(nombre="TP1", descripcion="d1"),
        Consigna(nombre="TP2", descripcion="d2"),
    ])
    db_session.commit()
    r = client.get("/api/consignas")
    assert r.status_code == 200
    assert len(r.json()) == 2


# ---------------------------------------------------------------------------
# GET /api/consignas/{id}
# ---------------------------------------------------------------------------

def test_obtener_consigna_existente(client, consigna_simple):
    r = client.get(f"/api/consignas/{consigna_simple.id}")
    assert r.status_code == 200
    assert r.json()["nombre"] == "TP1 Básico"


def test_obtener_consigna_no_existente(client):
    r = client.get("/api/consignas/9999")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/analizar — validación de entrada
# ---------------------------------------------------------------------------

def test_analizar_archivo_no_zip_retorna_400(client, consigna_simple):
    r = client.post(
        "/api/analizar",
        files={"archivo": ("entrega.txt", b"contenido", "text/plain")},
        data={"consigna_id": str(consigna_simple.id), "nombre_alumno": "Juan"},
    )
    assert r.status_code == 400
    assert "ZIP" in r.json()["detail"] or "RAR" in r.json()["detail"]


def test_analizar_consigna_inexistente_retorna_404(client):
    zip_bytes = make_zip({"main.c": HELLO_C})
    r = post_analizar(client, zip_bytes, consigna_id=9999)
    assert r.status_code == 404


def test_analizar_zip_corrupto_retorna_400(client, consigna_simple):
    r = post_analizar(client, b"esto no es un zip", consigna_simple.id)
    assert r.status_code == 400
    assert "corrupto" in r.json()["detail"].lower()


def test_analizar_zip_con_path_traversal_retorna_400(client, consigna_simple):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../malicioso.c", "int main(){return 0;}")
    r = post_analizar(client, buf.getvalue(), consigna_simple.id)
    assert r.status_code == 400
    assert "sospechoso" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# POST /api/analizar — flujo exitoso
# ---------------------------------------------------------------------------

def test_analizar_compilacion_exitosa_cumple_consigna(client, consigna_simple):
    zip_bytes = make_zip({"main.c": HELLO_C})
    with patch("app.api.routes.compile_c_files", return_value=COMPILE_OK), \
         patch("app.api.routes.run_tests", return_value=[]):
        r = post_analizar(client, zip_bytes, consigna_simple.id, nombre="María García")
    assert r.status_code == 200
    data = r.json()
    assert data["student_name"] == "María García"
    assert data["cumple_consigna"] is True
    assert data["compilacion"]["success"] is True
    assert data["compilacion"]["errors"] == []


def test_analizar_compilacion_fallida_no_cumple_consigna(client, consigna_simple):
    zip_bytes = make_zip({"main.c": "int main(){ return"})
    with patch("app.api.routes.compile_c_files", return_value=COMPILE_FAIL), \
         patch("app.api.routes.run_tests", return_value=[]):
        r = post_analizar(client, zip_bytes, consigna_simple.id)
    assert r.status_code == 200
    data = r.json()
    assert data["cumple_consigna"] is False
    assert data["compilacion"]["success"] is False
    assert len(data["compilacion"]["errors"]) > 0


def test_analizar_compilacion_con_warnings_sigue_siendo_exitosa(client, consigna_simple):
    zip_bytes = make_zip({"main.c": HELLO_C})
    compile_warnings = CompilationResult(
        success=True,
        errors=[],
        warnings=["main.c:1:5: warning: unused variable 'x'"],
    )
    with patch("app.api.routes.compile_c_files", return_value=compile_warnings), \
         patch("app.api.routes.run_tests", return_value=[]):
        r = post_analizar(client, zip_bytes, consigna_simple.id)
    assert r.status_code == 200
    data = r.json()
    assert data["compilacion"]["success"] is True
    assert len(data["compilacion"]["warnings"]) == 1


# ---------------------------------------------------------------------------
# POST /api/analizar — checks estáticos reales (sin mock)
# ---------------------------------------------------------------------------

def test_analizar_check_estatico_pasa(client, consigna_con_checks):
    zip_bytes = make_zip({"main.c": MALLOC_C})
    with patch("app.api.routes.compile_c_files", return_value=COMPILE_OK), \
         patch("app.api.routes.run_tests", return_value=[{"descripcion": "Imprime 42", "passed": True, "output": "42", "error": ""}]):
        r = post_analizar(client, zip_bytes, consigna_con_checks.id)
    assert r.status_code == 200
    data = r.json()
    assert len(data["checks_estaticos"]) == 1
    assert data["checks_estaticos"][0]["passed"] is True
    assert data["checks_estaticos"][0]["descripcion"] == "Usa malloc"


def test_analizar_check_estatico_falla_no_cumple_consigna(client, consigna_con_checks):
    # Código sin malloc
    zip_bytes = make_zip({"main.c": HELLO_C})
    with patch("app.api.routes.compile_c_files", return_value=COMPILE_OK), \
         patch("app.api.routes.run_tests", return_value=[{"descripcion": "Imprime 42", "passed": True, "output": "42", "error": ""}]):
        r = post_analizar(client, zip_bytes, consigna_con_checks.id)
    assert r.status_code == 200
    data = r.json()
    assert data["checks_estaticos"][0]["passed"] is False
    assert data["cumple_consigna"] is False


# ---------------------------------------------------------------------------
# POST /api/analizar — tests I/O
# ---------------------------------------------------------------------------

def test_analizar_test_io_pasa(client, consigna_con_checks):
    zip_bytes = make_zip({"main.c": MALLOC_C})
    test_result = [{"descripcion": "Imprime 42", "passed": True, "output": "42\n", "error": ""}]
    with patch("app.api.routes.compile_c_files", return_value=COMPILE_OK), \
         patch("app.api.routes.run_tests", return_value=test_result):
        r = post_analizar(client, zip_bytes, consigna_con_checks.id)
    assert r.status_code == 200
    assert r.json()["tests_io"][0]["passed"] is True


def test_analizar_test_io_falla_no_cumple_consigna(client, consigna_con_checks):
    zip_bytes = make_zip({"main.c": MALLOC_C})
    test_result = [{"descripcion": "Imprime 42", "passed": False, "output": "0\n", "error": ""}]
    with patch("app.api.routes.compile_c_files", return_value=COMPILE_OK), \
         patch("app.api.routes.run_tests", return_value=test_result):
        r = post_analizar(client, zip_bytes, consigna_con_checks.id)
    assert r.status_code == 200
    data = r.json()
    assert data["tests_io"][0]["passed"] is False
    assert data["cumple_consigna"] is False


# ---------------------------------------------------------------------------
# POST /api/analizar — estructura de la respuesta
# ---------------------------------------------------------------------------

def test_analizar_respuesta_tiene_todos_los_campos(client, consigna_simple):
    zip_bytes = make_zip({"main.c": HELLO_C})
    with patch("app.api.routes.compile_c_files", return_value=COMPILE_OK), \
         patch("app.api.routes.run_tests", return_value=[]):
        r = post_analizar(client, zip_bytes, consigna_simple.id, nombre="Ana Lopez")
    assert r.status_code == 200
    data = r.json()
    assert "student_name" in data
    assert "cumple_consigna" in data
    assert "compilacion" in data
    assert "checks_estaticos" in data
    assert "tests_io" in data
    assert "errors" in data["compilacion"]
    assert "warnings" in data["compilacion"]
    assert "success" in data["compilacion"]


def test_analizar_zip_vacio_sin_c_no_compila(client, consigna_simple):
    zip_bytes = make_zip({"readme.txt": "sin código"})
    # No llegamos a Docker porque no hay .c — compile_c_files retorna error sin mock
    with patch("app.api.routes.run_tests", return_value=[]):
        r = post_analizar(client, zip_bytes, consigna_simple.id)
    assert r.status_code == 200
    data = r.json()
    assert data["compilacion"]["success"] is False
    assert data["cumple_consigna"] is False
