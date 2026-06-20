import io
import os
import zipfile
import tempfile
import pytest


def make_zip(files: dict[str, str]) -> bytes:
    """Crea un ZIP en memoria. files = {nombre: contenido}"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


@pytest.fixture
def zip_factory(tmp_path):
    """Devuelve una función que escribe un ZIP en disco y retorna su path."""
    def _factory(files: dict[str, str], filename="entrega.zip") -> str:
        path = str(tmp_path / filename)
        data = make_zip(files)
        with open(path, "wb") as f:
            f.write(data)
        return path
    return _factory


@pytest.fixture
def extract_dir(tmp_path):
    d = tmp_path / "extracted"
    d.mkdir()
    return str(d)


HELLO_C = """
#include <stdio.h>
int main() {
    printf("Hola mundo\\n");
    return 0;
}
"""

MALLOC_C = """
#include <stdio.h>
#include <stdlib.h>
int main() {
    int *p = malloc(sizeof(int) * 10);
    for (int i = 0; i < 10; i++) p[i] = i;
    printf("%d\\n", p[9]);
    free(p);
    return 0;
}
"""

SYNTAX_ERROR_C = """
#include <stdio.h>
int main() {
    printf("falta el return
    return 0;
}
"""
