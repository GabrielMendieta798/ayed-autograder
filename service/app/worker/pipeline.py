import os
import tempfile
import time

from app.services.compiler import compile_c_files
from app.services.static_analyzer import run_static_checks
from app.services.test_runner import run_tests
from app.services.zip_validator import validate_and_extract
from app.worker.schemas import (
    CompilationResult,
    GradeRequest,
    GradeResult,
    ScoreResult,
    StaticAnalysisResult,
    StaticCheckResult,
    TestCaseResult,
)


def run_worker_grade_job(archive_path: str, request: GradeRequest) -> GradeResult:
    """Ejecuta una correccion sin base de datos ni efectos externos."""
    started_at = time.monotonic()

    with tempfile.TemporaryDirectory(prefix="autocorrector-worker-") as workspace:
        extract_dir = os.path.join(workspace, "submission")
        os.makedirs(extract_dir)
        source_files = validate_and_extract(archive_path, extract_dir)

        legacy_compilation = compile_c_files(source_files)
        compilation = CompilationResult(**legacy_compilation.model_dump())

        static_raw = run_static_checks(source_files, request.static_checks)
        static_results = [
            StaticCheckResult(
                name=check.name,
                passed=result["passed"],
                found=result["found"],
            )
            for check, result in zip(request.static_checks, static_raw)
        ]

        if compilation.success:
            tests_raw = run_tests(source_files, request.tests)
        else:
            compile_error = compilation.stderr or "; ".join(compilation.errors) or "El codigo no compilo"
            tests_raw = [
                {"passed": False, "output": "", "error": compile_error}
                for _ in request.tests
            ]

        test_results = []
        obtained = 0
        for test, raw in zip(request.tests, tests_raw):
            points = test.points if raw["passed"] else 0
            obtained += points
            test_results.append(TestCaseResult(
                name=test.name,
                passed=raw["passed"],
                input=test.input,
                expected_output=test.expected_output,
                actual_output=raw.get("output", ""),
                stderr=raw.get("error", ""),
                error=raw.get("error", "") if not raw["passed"] else "",
                points_obtained=points,
                points_maximum=test.points,
            ))

    duration_ms = int((time.monotonic() - started_at) * 1000)
    return GradeResult(
        job_id=request.job_id,
        status="completed",
        compilation=compilation,
        tests=test_results,
        static_analysis=StaticAnalysisResult(checks=static_results),
        score=ScoreResult(
            obtained=obtained,
            maximum=sum(test.points for test in request.tests),
        ),
        errors=[],
        duration_ms=duration_ms,
    )
