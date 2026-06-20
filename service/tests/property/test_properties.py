"""
Tests de propiedad con Hypothesis.
Verifican invariantes del sistema ante inputs generados aleatoriamente.
"""
import io
import os
import zipfile
import tempfile
import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from app.services.zip_validator import validate_and_extract
from app.services.static_analyzer import run_static_checks
from unittest.mock import MagicMock
from app.models.models import CheckEstatico


# ---------------------------------------------------------------------------
# zip_validator: invariantes de seguridad
# ---------------------------------------------------------------------------

def _write_zip(files: dict[str, bytes], tmp_path: str) -> str:
    path = os.path.join(tmp_path, "test.zip")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    with open(path, "wb") as f:
        f.write(buf.getvalue())
    return path


safe_filename = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_"),
    min_size=1, max_size=20,
).map(lambda s: s + ".c")

c_content = st.text(min_size=0, max_size=500).map(lambda s: s.encode("utf-8", errors="replace"))


@given(files=st.dictionaries(safe_filename, c_content, min_size=0, max_size=10))
@settings(max_examples=50)
def test_zip_valido_nunca_lanza_excepcion(files):
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = _write_zip(files, tmp)
        extract = os.path.join(tmp, "out")
        os.makedirs(extract)
        result = validate_and_extract(zip_path, extract)
        # Invariante: siempre retorna una lista (nunca explota)
        assert isinstance(result, list)
        # Invariante: solo devuelve .c y .h
        for f in result:
            assert f.endswith((".c", ".h"))


@given(
    prefix=st.sampled_from(["../", "../../", "/"]),
    rest=st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=1, max_size=10),
)
@settings(max_examples=30)
def test_path_traversal_siempre_bloqueado(prefix, rest):
    filename = prefix + rest + ".c"
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = os.path.join(tmp, "t.zip")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(filename, "int main(){return 0;}")
        with open(zip_path, "wb") as f:
            f.write(buf.getvalue())
        extract = os.path.join(tmp, "out")
        os.makedirs(extract)
        with pytest.raises(ValueError):
            validate_and_extract(zip_path, extract)


# ---------------------------------------------------------------------------
# static_analyzer: invariantes de resultados
# ---------------------------------------------------------------------------

def make_check(pattern: str, check_type: str = "exists", min_count: int = 1) -> MagicMock:
    c = MagicMock(spec=CheckEstatico)
    c.descripcion = "test"
    c.pattern = pattern
    c.check_type = check_type
    c.min_count = min_count
    return c


safe_pattern = st.sampled_from([r"\bmalloc\b", r"\bfree\b", r"void\s*\*", r"\bprintf\b", r"struct\s+\w+"])
safe_code = st.text(min_size=0, max_size=1000)


@given(code=safe_code, pattern=safe_pattern)
@settings(max_examples=50)
def test_static_check_siempre_retorna_bool(code, pattern):
    with tempfile.TemporaryDirectory() as tmp:
        f = os.path.join(tmp, "test.c")
        with open(f, "w", encoding="utf-8", errors="replace") as fh:
            fh.write(code)
        check = make_check(pattern)
        results = run_static_checks([f], [check])
        assert len(results) == 1
        assert isinstance(results[0]["passed"], bool)
        assert isinstance(results[0]["found"], int)
        assert results[0]["found"] >= 0


@given(code=safe_code, n=st.integers(min_value=1, max_value=20))
@settings(max_examples=30)
def test_count_gte_consistente_con_found(code, n):
    """Si found >= n → passed; si found < n → not passed."""
    with tempfile.TemporaryDirectory() as tmp:
        f = os.path.join(tmp, "test.c")
        with open(f, "w", encoding="utf-8", errors="replace") as fh:
            fh.write(code)
        check = make_check(r"\bmalloc\b", check_type="count_gte", min_count=n)
        results = run_static_checks([f], [check])
        r = results[0]
        if r["found"] >= n:
            assert r["passed"] is True
        else:
            assert r["passed"] is False
