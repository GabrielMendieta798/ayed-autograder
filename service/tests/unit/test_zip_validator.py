import io
import os
import zipfile
import pytest
from tests.conftest import make_zip
from app.services.zip_validator import validate_and_extract, MAX_FILES, MAX_UNCOMPRESSED_MB


# ---------------------------------------------------------------------------
# ZIP válidos
# ---------------------------------------------------------------------------

def test_zip_valido_extrae_c_files(zip_factory, extract_dir):
    path = zip_factory({"main.c": "int main(){return 0;}", "utils.h": "void f();"})
    files = validate_and_extract(path, extract_dir)
    names = [os.path.basename(f) for f in files]
    assert "main.c" in names
    assert "utils.h" in names


def test_zip_ignora_extensiones_no_permitidas(zip_factory, extract_dir):
    path = zip_factory({"main.c": "int main(){return 0;}", "readme.txt": "ignorame"})
    files = validate_and_extract(path, extract_dir)
    names = [os.path.basename(f) for f in files]
    assert "readme.txt" not in names
    assert "main.c" in names


def test_zip_con_subdirectorio(zip_factory, extract_dir, tmp_path):
    # Crear ZIP con estructura de carpeta
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("src/main.c", "int main(){return 0;}")
    zip_path = str(tmp_path / "sub.zip")
    with open(zip_path, "wb") as f:
        f.write(buf.getvalue())
    files = validate_and_extract(zip_path, extract_dir)
    assert any(f.endswith("main.c") for f in files)


def test_zip_solo_headers(zip_factory, extract_dir):
    path = zip_factory({"utils.h": "void f();"})
    files = validate_and_extract(path, extract_dir)
    assert any(f.endswith("utils.h") for f in files)


# ---------------------------------------------------------------------------
# Validaciones de seguridad
# ---------------------------------------------------------------------------

def test_path_traversal_bloqueado(extract_dir, tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../malicioso.c", "int main(){return 0;}")
    zip_path = str(tmp_path / "traversal.zip")
    with open(zip_path, "wb") as f:
        f.write(buf.getvalue())
    with pytest.raises(ValueError, match="sospechoso"):
        validate_and_extract(zip_path, extract_dir)


def test_path_absoluto_bloqueado(extract_dir, tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        info = zipfile.ZipInfo("/etc/passwd")
        zf.writestr(info, "root:x:0:0")
    zip_path = str(tmp_path / "abs.zip")
    with open(zip_path, "wb") as f:
        f.write(buf.getvalue())
    with pytest.raises(ValueError, match="sospechoso"):
        validate_and_extract(zip_path, extract_dir)


def test_demasiados_archivos_rechazado(extract_dir, tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for i in range(MAX_FILES + 1):
            zf.writestr(f"file{i}.c", "int main(){return 0;}")
    zip_path = str(tmp_path / "big.zip")
    with open(zip_path, "wb") as f:
        f.write(buf.getvalue())
    with pytest.raises(ValueError, match="demasiados"):
        validate_and_extract(zip_path, extract_dir)


def test_zip_corrupto_rechazado(extract_dir, tmp_path):
    zip_path = str(tmp_path / "corrupto.zip")
    with open(zip_path, "wb") as f:
        f.write(b"esto no es un zip")
    with pytest.raises(ValueError, match="corrupto"):
        validate_and_extract(zip_path, extract_dir)


def test_zip_vacio_retorna_lista_vacia(zip_factory, extract_dir):
    path = zip_factory({})
    files = validate_and_extract(path, extract_dir)
    assert files == []


def test_zip_solo_archivos_no_permitidos(zip_factory, extract_dir):
    path = zip_factory({"foto.jpg": b"\xff\xd8\xff", "notas.pdf": b"%PDF"})
    files = validate_and_extract(path, extract_dir)
    assert files == []
