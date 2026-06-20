"""
Tests funcionales de POST /api/submissions/analyze y GET /api/submissions/{id}.
Usan TestClient con SQLite en memoria.
Mockean compile_c_files y run_tests (requieren Docker).
validate_and_extract y run_static_checks corren real.
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
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_engine(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path}/test.db",
        connect_args={"check_same_thread": False},
    )
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
    c = Consigna(nombre="TP1", descripcion="Hello world")
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


@pytest.fixture
def consigna_con_test(db_session) -> Consigna:
    """Consigna con un CasoPrueba de 5 puntos."""
    c = Consigna(nombre="TP2", descripcion="Calcula cuadrado")
    db_session.add(c)
    db_session.flush()
    db_session.add(CasoPrueba(
        consigna_id=c.id,
        descripcion="5 al cuadrado",
        input="5\n",
        expected_output="25\n",
        check_type="exact",
        timeout_seg=5,
        points=5,
    ))
    db_session.commit()
    db_session.refresh(c)
    return c


@pytest.fixture
def consigna_dos_tests(db_session) -> Consigna:
    """Consigna con dos CasoPrueba de distinto puntaje."""
    c = Consigna(nombre="TP3", descripcion="Suma y resta")
    db_session.add(c)
    db_session.flush()
    db_session.add(CasoPrueba(
        consigna_id=c.id,
        descripcion="Suma",
        input="2 3\n",
        expected_output="5",
        check_type="contains",
        timeout_seg=5,
        points=3,
    ))
    db_session.add(CasoPrueba(
        consigna_id=c.id,
        descripcion="Resta",
        input="5 2\n",
        expected_output="3",
        check_type="contains",
        timeout_seg=5,
        points=7,
    ))
    db_session.commit()
    db_session.refresh(c)
    return c


@pytest.fixture
def consigna_con_check_y_test(db_session) -> Consigna:
    c = Consigna(nombre="TP4", descripcion="Usar malloc")
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
        descripcion="Imprime OK",
        input="",
        expected_output="OK",
        check_type="contains",
        timeout_seg=5,
        points=10,
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


def post_analyze(client, zip_bytes: bytes, consigna_id: int,
                 nombre: str = "Juan Perez", filename: str = "entrega.zip"):
    return client.post(
        "/api/submissions/analyze",
        files={"archivo": (filename, zip_bytes, "application/zip")},
        data={"consigna_id": str(consigna_id), "nombre_alumno": nombre},
    )


COMPILE_OK = CompilationResult(success=True, errors=[], warnings=[])
COMPILE_FAIL = CompilationResult(success=False, errors=["main.c:3:1: error: expected ';'"], warnings=[])

HELLO_C = '#include <stdio.h>\nint main(){printf("OK\\n");return 0;}'
MALLOC_C = '#include <stdlib.h>\nint main(){int*p=malloc(4);free(p);printf("OK\\n");return 0;}'


# ---------------------------------------------------------------------------
# Validación de entrada
# ---------------------------------------------------------------------------

def test_analyze_archivo_no_zip_retorna_400(client, consigna_simple):
    r = client.post(
        "/api/submissions/analyze",
        files={"archivo": ("entrega.txt", b"nada", "text/plain")},
        data={"consigna_id": str(consigna_simple.id), "nombre_alumno": "Ana"},
    )
    assert r.status_code == 400


def test_analyze_consigna_inexistente_retorna_404(client):
    zip_bytes = make_zip({"main.c": HELLO_C})
    r = post_analyze(client, zip_bytes, consigna_id=9999)
    assert r.status_code == 404


def test_analyze_zip_corrupto_retorna_400(client, consigna_simple):
    r = post_analyze(client, b"esto no es un zip", consigna_simple.id)
    assert r.status_code == 400


def test_analyze_zip_con_path_traversal_retorna_400(client, consigna_simple):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../malicioso.c", "int main(){return 0;}")
    r = post_analyze(client, buf.getvalue(), consigna_simple.id)
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Flujo exitoso — estructura de la respuesta
# ---------------------------------------------------------------------------

def test_analyze_retorna_submission_con_id(client, consigna_simple):
    zip_bytes = make_zip({"main.c": HELLO_C})
    with patch("app.services.pipeline.compile_c_files", return_value=COMPILE_OK), \
         patch("app.services.pipeline.run_tests", return_value=[]):
        r = post_analyze(client, zip_bytes, consigna_simple.id, nombre="María López")
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data["id"] > 0
    assert data["student_name"] == "María López"
    assert data["status"] == "completed"


def test_analyze_respuesta_tiene_todos_los_campos(client, consigna_simple):
    zip_bytes = make_zip({"main.c": HELLO_C})
    with patch("app.services.pipeline.compile_c_files", return_value=COMPILE_OK), \
         patch("app.services.pipeline.run_tests", return_value=[]):
        r = post_analyze(client, zip_bytes, consigna_simple.id)
    assert r.status_code == 200
    data = r.json()
    for campo in ["id", "student_name", "consigna_id", "original_filename",
                  "status", "score", "max_score", "feedback_llm", "created_at",
                  "source_files", "cumple_consigna", "compilacion",
                  "checks_estaticos", "tests_io"]:
        assert campo in data, f"falta campo: {campo}"


def test_analyze_source_files_incluye_archivos_c(client, consigna_simple):
    zip_bytes = make_zip({"main.c": HELLO_C, "utils.c": HELLO_C, "utils.h": ""})
    with patch("app.services.pipeline.compile_c_files", return_value=COMPILE_OK), \
         patch("app.services.pipeline.run_tests", return_value=[]):
        r = post_analyze(client, zip_bytes, consigna_simple.id)
    assert r.status_code == 200
    files = r.json()["source_files"]
    assert "main.c" in files
    assert "utils.c" in files
    assert "utils.h" in files


def test_analyze_compilacion_ok_en_respuesta(client, consigna_simple):
    zip_bytes = make_zip({"main.c": HELLO_C})
    with patch("app.services.pipeline.compile_c_files", return_value=COMPILE_OK), \
         patch("app.services.pipeline.run_tests", return_value=[]):
        r = post_analyze(client, zip_bytes, consigna_simple.id)
    data = r.json()
    assert data["compilacion"]["success"] is True
    assert data["compilacion"]["errors"] == []


def test_analyze_compilacion_falla_en_respuesta(client, consigna_simple):
    zip_bytes = make_zip({"main.c": HELLO_C})
    with patch("app.services.pipeline.compile_c_files", return_value=COMPILE_FAIL), \
         patch("app.services.pipeline.run_tests", return_value=[]):
        r = post_analyze(client, zip_bytes, consigna_simple.id)
    data = r.json()
    assert data["compilacion"]["success"] is False
    assert len(data["compilacion"]["errors"]) > 0
    assert data["cumple_consigna"] is False


# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------

def test_analyze_score_cero_sin_tests(client, consigna_simple):
    zip_bytes = make_zip({"main.c": HELLO_C})
    with patch("app.services.pipeline.compile_c_files", return_value=COMPILE_OK), \
         patch("app.services.pipeline.run_tests", return_value=[]):
        r = post_analyze(client, zip_bytes, consigna_simple.id)
    data = r.json()
    assert data["score"] == 0
    assert data["max_score"] == 0


def test_analyze_score_completo_cuando_test_pasa(client, consigna_con_test):
    zip_bytes = make_zip({"main.c": HELLO_C})
    mock_results = [{"descripcion": "5 al cuadrado", "passed": True, "output": "25\n", "error": ""}]
    with patch("app.services.pipeline.compile_c_files", return_value=COMPILE_OK), \
         patch("app.services.pipeline.run_tests", return_value=mock_results):
        r = post_analyze(client, zip_bytes, consigna_con_test.id)
    data = r.json()
    assert data["score"] == 5
    assert data["max_score"] == 5


def test_analyze_score_cero_cuando_test_falla(client, consigna_con_test):
    zip_bytes = make_zip({"main.c": HELLO_C})
    mock_results = [{"descripcion": "5 al cuadrado", "passed": False, "output": "0\n", "error": ""}]
    with patch("app.services.pipeline.compile_c_files", return_value=COMPILE_OK), \
         patch("app.services.pipeline.run_tests", return_value=mock_results):
        r = post_analyze(client, zip_bytes, consigna_con_test.id)
    data = r.json()
    assert data["score"] == 0
    assert data["max_score"] == 5


def test_analyze_score_parcial_con_dos_tests(client, consigna_dos_tests):
    zip_bytes = make_zip({"main.c": HELLO_C})
    mock_results = [
        {"descripcion": "Suma", "passed": True, "output": "5", "error": ""},
        {"descripcion": "Resta", "passed": False, "output": "0", "error": ""},
    ]
    with patch("app.services.pipeline.compile_c_files", return_value=COMPILE_OK), \
         patch("app.services.pipeline.run_tests", return_value=mock_results):
        r = post_analyze(client, zip_bytes, consigna_dos_tests.id)
    data = r.json()
    assert data["score"] == 3       # solo el de suma
    assert data["max_score"] == 10  # 3 + 7


# ---------------------------------------------------------------------------
# Campos completos de TestResultOut
# ---------------------------------------------------------------------------

def test_analyze_test_io_tiene_campos_completos(client, consigna_con_test):
    zip_bytes = make_zip({"main.c": HELLO_C})
    mock_results = [{"descripcion": "5 al cuadrado", "passed": True, "output": "25\n", "error": ""}]
    with patch("app.services.pipeline.compile_c_files", return_value=COMPILE_OK), \
         patch("app.services.pipeline.run_tests", return_value=mock_results):
        r = post_analyze(client, zip_bytes, consigna_con_test.id)
    assert r.status_code == 200
    test = r.json()["tests_io"][0]
    assert test["descripcion"] == "5 al cuadrado"
    assert test["passed"] is True
    assert test["points_obtained"] == 5
    assert test["input_used"] == "5\n"
    assert test["expected_output"] == "25\n"
    assert test["actual_output"] == "25\n"


def test_analyze_test_fallido_points_obtained_es_cero(client, consigna_con_test):
    zip_bytes = make_zip({"main.c": HELLO_C})
    mock_results = [{"descripcion": "5 al cuadrado", "passed": False, "output": "0\n", "error": "timeout"}]
    with patch("app.services.pipeline.compile_c_files", return_value=COMPILE_OK), \
         patch("app.services.pipeline.run_tests", return_value=mock_results):
        r = post_analyze(client, zip_bytes, consigna_con_test.id)
    test = r.json()["tests_io"][0]
    assert test["passed"] is False
    assert test["points_obtained"] == 0
    assert test["error_message"] == "timeout"


# ---------------------------------------------------------------------------
# cumple_consigna
# ---------------------------------------------------------------------------

def test_analyze_cumple_consigna_true_cuando_todo_pasa(client, consigna_con_check_y_test):
    zip_bytes = make_zip({"main.c": MALLOC_C})
    mock_results = [{"descripcion": "Imprime OK", "passed": True, "output": "OK\n", "error": ""}]
    with patch("app.services.pipeline.compile_c_files", return_value=COMPILE_OK), \
         patch("app.services.pipeline.run_tests", return_value=mock_results):
        r = post_analyze(client, zip_bytes, consigna_con_check_y_test.id)
    data = r.json()
    assert data["cumple_consigna"] is True
    assert data["checks_estaticos"][0]["passed"] is True


def test_analyze_cumple_consigna_false_si_check_falla(client, consigna_con_check_y_test):
    # HELLO_C no tiene malloc
    zip_bytes = make_zip({"main.c": HELLO_C})
    mock_results = [{"descripcion": "Imprime OK", "passed": True, "output": "OK\n", "error": ""}]
    with patch("app.services.pipeline.compile_c_files", return_value=COMPILE_OK), \
         patch("app.services.pipeline.run_tests", return_value=mock_results):
        r = post_analyze(client, zip_bytes, consigna_con_check_y_test.id)
    data = r.json()
    assert data["cumple_consigna"] is False
    assert data["checks_estaticos"][0]["passed"] is False


# ---------------------------------------------------------------------------
# GET /api/submissions/{id}
# ---------------------------------------------------------------------------

def test_get_submission_no_existente_retorna_404(client):
    r = client.get("/api/submissions/9999")
    assert r.status_code == 404


def test_get_submission_devuelve_datos_guardados(client, consigna_con_test):
    zip_bytes = make_zip({"main.c": HELLO_C})
    mock_results = [{"descripcion": "5 al cuadrado", "passed": True, "output": "25\n", "error": ""}]
    with patch("app.services.pipeline.compile_c_files", return_value=COMPILE_OK), \
         patch("app.services.pipeline.run_tests", return_value=mock_results):
        post_r = post_analyze(client, zip_bytes, consigna_con_test.id, nombre="Pedro")
    assert post_r.status_code == 200
    submission_id = post_r.json()["id"]

    get_r = client.get(f"/api/submissions/{submission_id}")
    assert get_r.status_code == 200
    data = get_r.json()
    assert data["id"] == submission_id
    assert data["student_name"] == "Pedro"
    assert data["score"] == 5
    assert data["status"] == "completed"
    assert len(data["tests_io"]) == 1
    assert data["tests_io"][0]["passed"] is True
