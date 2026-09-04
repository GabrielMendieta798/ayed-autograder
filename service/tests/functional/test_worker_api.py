import json

import httpx
import pytest
from unittest.mock import patch

from app.main import app
from app.models.schemas import CompilationResult as LegacyCompilationResult
from tests.conftest import make_zip


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


@pytest.mark.asyncio
async def test_grade_devuelve_contrato_del_worker(client):
    config = {
        "job_id": "demo-job-1",
        "tests": [{
            "name": "Suma simple",
            "input": "3 + 5\n",
            "expected_output": "8",
            "check_type": "contains",
            "points": 100,
        }],
        "static_checks": [],
    }
    compilation = LegacyCompilationResult(
        success=True, errors=[], warnings=[], stdout="", stderr="", exit_code=0
    )

    with (
        patch("app.worker.pipeline.compile_c_files", return_value=compilation),
        patch("app.worker.pipeline.run_tests", return_value=[{
            "descripcion": "Suma simple",
            "passed": True,
            "output": "8\n",
            "error": "",
        }]),
    ):
        response = await client.post(
            "/grade",
            files={"archivo": ("entrega.zip", make_zip({"main.c": "int main(void){return 0;}"}), "application/zip")},
            data={"config": json.dumps(config)},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == "demo-job-1"
    assert body["status"] == "completed"
    assert body["compilation"]["exit_code"] == 0
    assert body["tests"][0]["actual_output"] == "8\n"
    assert body["score"] == {"obtained": 100, "maximum": 100}
    assert isinstance(body["duration_ms"], int)


@pytest.mark.asyncio
async def test_grade_rechaza_config_invalida(client):
    response = await client.post(
        "/grade",
        files={"archivo": ("entrega.zip", make_zip({"main.c": ""}), "application/zip")},
        data={"config": "{}"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_grade_rechaza_archivo_que_no_es_zip(client):
    response = await client.post(
        "/grade",
        files={"archivo": ("entrega.rar", b"contenido", "application/octet-stream")},
        data={"config": json.dumps({"job_id": "job-1"})},
    )

    assert response.status_code == 400
