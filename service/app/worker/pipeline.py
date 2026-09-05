import os
import tempfile
import time

from app.services.compiler import compile_c_files
from app.services.static_analyzer import run_static_checks
from app.services.test_runner import run_tests
from app.services.zip_validator import validate_and_extract
from app.worker.domain import (
    CompilationEvidence,
    GradeContext,
    GradeEvidence,
    GradeJob,
    ScoreEvidence,
    StaticCheckEvidence,
    TestEvidence,
)


def run_worker_grade_job(job: GradeJob) -> GradeEvidence:
    """Ejecuta una correccion sin base de datos ni efectos externos."""
    started_at = time.monotonic()
    context = GradeContext(job=job)

    with tempfile.TemporaryDirectory(prefix="autocorrector-worker-") as workspace:
        extract_dir = os.path.join(workspace, "submission")
        os.makedirs(extract_dir)
        context.source_files = validate_and_extract(job.archive_path, extract_dir)

        compilation_result = compile_c_files(context.source_files)
        context.compilation = CompilationEvidence(
            success=compilation_result.success,
            stdout=compilation_result.stdout,
            stderr=compilation_result.stderr,
            exit_code=compilation_result.exit_code,
            errors=tuple(compilation_result.errors),
            warnings=tuple(compilation_result.warnings),
        )

        static_raw = run_static_checks(context.source_files, list(job.static_checks))
        context.static_checks = [
            StaticCheckEvidence(
                name=check.name,
                passed=result["passed"],
                found=result["found"],
            )
            for check, result in zip(job.static_checks, static_raw)
        ]

        if context.compilation.success:
            tests_raw = run_tests(context.source_files, list(job.tests))
        else:
            compile_error = (
                context.compilation.stderr
                or "; ".join(context.compilation.errors)
                or "El codigo no compilo"
            )
            tests_raw = [
                {"passed": False, "output": "", "error": compile_error}
                for _ in job.tests
            ]

        obtained = 0
        for test, raw in zip(job.tests, tests_raw):
            points = test.points if raw["passed"] else 0
            obtained += points
            context.tests.append(TestEvidence(
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

        context.score = ScoreEvidence(
            obtained=obtained,
            maximum=sum(test.points for test in job.tests),
        )

    duration_ms = int((time.monotonic() - started_at) * 1000)
    return GradeEvidence(
        job_id=job.job_id,
        status="completed",
        compilation=context.compilation,
        tests=tuple(context.tests),
        static_analysis=tuple(context.static_checks),
        score=context.score,
        errors=tuple(context.errors),
        duration_ms=duration_ms,
    )
