from unittest.mock import patch

from app.models.schemas import CompilationResult as LegacyCompilationResult
from app.worker.pipeline import run_worker_grade_job
from app.worker.schemas import GradeRequest


def test_worker_pipeline_calcula_resultado_sin_base_de_datos(zip_factory):
    archive = zip_factory({"src/main.c": "int main(void) { return 0; }"})
    request = GradeRequest.model_validate({
        "job_id": "demo-job-1",
        "tests": [{
            "name": "Suma simple",
            "input": "3 + 5\n",
            "expected_output": "8",
            "check_type": "contains",
            "points": 100,
        }],
        "static_checks": [{
            "name": "Tiene main",
            "pattern": r"\bmain\s*\(",
            "check_type": "exists",
        }],
    })

    compilation = LegacyCompilationResult(
        success=True,
        errors=[],
        warnings=[],
        stdout="",
        stderr="",
        exit_code=0,
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
        result = run_worker_grade_job(archive, request)

    assert result.job_id == "demo-job-1"
    assert result.status == "completed"
    assert result.compilation.success is True
    assert result.tests[0].passed is True
    assert result.tests[0].actual_output == "8\n"
    assert result.static_analysis.checks[0].passed is True
    assert result.score.obtained == 100
    assert result.score.maximum == 100


def test_worker_pipeline_no_ejecuta_tests_si_no_compila(zip_factory):
    archive = zip_factory({"main.c": "int main(void) {"})
    request = GradeRequest.model_validate({
        "job_id": "compile-fail",
        "tests": [{"name": "Caso", "points": 10}],
    })
    compilation = LegacyCompilationResult(
        success=False,
        errors=["error: expected declaration"],
        warnings=[],
        stderr="error: expected declaration",
        exit_code=1,
    )

    with (
        patch("app.worker.pipeline.compile_c_files", return_value=compilation),
        patch("app.worker.pipeline.run_tests") as run_tests_mock,
    ):
        result = run_worker_grade_job(archive, request)

    run_tests_mock.assert_not_called()
    assert result.tests[0].passed is False
    assert result.score.obtained == 0
    assert result.score.maximum == 10
