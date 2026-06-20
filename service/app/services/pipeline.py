"""
Pipeline de corrección de entregas.

Flujo:
  1. Validar y extraer ZIP
  2. Compilar con GCC (una vez)
  3. Checks estáticos (regex sobre fuente)
  4. Tests I/O (usa el binario del paso 2)
  5. Calcular score
  6. LLM feedback (si hay API key configurada)
  7. Guardar TestResult por cada caso de prueba
  8. Actualizar Submission con status=completed
"""
import json
import os
import shutil
import tempfile
import time

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Consigna, Submission, TestResult
from app.models.schemas import SubmissionOut, TestResultOut, CompilationResult, StaticCheckResult
from app.services.zip_validator import validate_and_extract
from app.services.compiler import compile_c_files
from app.services.static_analyzer import run_static_checks
from app.services.test_runner import run_tests


def run_pipeline(
    db: Session,
    student_name: str,
    consigna: Consigna,
    zip_path: str,
    original_filename: str,
    extract_dir: str,
) -> SubmissionOut:
    submission = Submission(
        student_name=student_name,
        consigna_id=consigna.id,
        original_filename=original_filename,
        status="running",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    try:
        result = _execute(db, submission, consigna, zip_path, extract_dir)
        return result
    except Exception as e:
        submission.status = "failed"
        submission.result_json = json.dumps({"error": str(e)})
        db.commit()
        raise


def _execute(
    db: Session,
    submission: Submission,
    consigna: Consigna,
    zip_path: str,
    extract_dir: str,
) -> SubmissionOut:
    # 1. Validar y extraer
    source_files = validate_and_extract(zip_path, extract_dir)
    source_basenames = [os.path.basename(f) for f in source_files]

    # 2. Compilar
    compilation = compile_c_files(source_files)

    # 3. Checks estáticos
    static_results = run_static_checks(source_files, consigna.checks_estaticos)

    # 4. Tests I/O
    test_results_raw = run_tests(source_files, consigna.casos_prueba)

    # 5. Score
    max_score = sum(caso.points for caso in consigna.casos_prueba)
    score = 0
    test_result_records: list[TestResult] = []

    for caso, raw in zip(consigna.casos_prueba, test_results_raw):
        points_obtained = caso.points if raw["passed"] else 0
        score += points_obtained
        tr = TestResult(
            submission_id=submission.id,
            test_case_id=caso.id,
            passed=raw["passed"],
            points_obtained=points_obtained,
            stdout=raw.get("output", ""),
            stderr=raw.get("error", ""),
            expected_output=caso.expected_output,
            actual_output=raw.get("output", ""),
            execution_time_ms=raw.get("execution_time_ms"),
            error_message=raw.get("error", "") if not raw["passed"] else "",
        )
        db.add(tr)
        test_result_records.append(tr)

    # 6. cumple_consigna
    cumple = (
        compilation.success
        and all(r["passed"] for r in static_results)
        and all(r["passed"] for r in test_results_raw)
    )

    # 7. LLM feedback (solo si hay API key)
    feedback_llm = None
    if settings.openai_api_key:
        try:
            from app.services.analyzer import analyze_submission
            feedback_llm, _ = analyze_submission(
                consigna=consigna.descripcion,
                c_files=[f for f in source_files if f.endswith(".c")],
                compilation=compilation,
            )
        except Exception:
            feedback_llm = None

    # 8. Persistir
    submission.status = "completed"
    submission.score = score
    submission.max_score = max_score
    submission.feedback_llm = feedback_llm
    submission.result_json = json.dumps({
        "cumple_consigna": cumple,
        "compilacion": compilation.model_dump(),
        "checks_estaticos": static_results,
        "source_files": source_basenames,
    })
    db.commit()
    db.refresh(submission)

    # 9. Construir respuesta
    return _build_response(submission, test_result_records, consigna)


def _build_response(
    submission: Submission,
    test_result_records: list[TestResult],
    consigna: Consigna,
) -> SubmissionOut:
    result = json.loads(submission.result_json or "{}")

    compilacion_data = result.get("compilacion")
    compilacion = CompilationResult(**compilacion_data) if compilacion_data else None

    checks_raw = result.get("checks_estaticos", [])
    checks = [StaticCheckResult(**c) for c in checks_raw]

    casos_by_id = {caso.id: caso for caso in consigna.casos_prueba}

    tests_io = [
        TestResultOut(
            id=tr.id,
            test_case_id=tr.test_case_id,
            descripcion=casos_by_id[tr.test_case_id].descripcion if tr.test_case_id and tr.test_case_id in casos_by_id else "",
            passed=tr.passed,
            points_obtained=tr.points_obtained,
            input_used=casos_by_id[tr.test_case_id].input if tr.test_case_id and tr.test_case_id in casos_by_id else "",
            expected_output=tr.expected_output,
            actual_output=tr.actual_output,
            stdout=tr.stdout,
            stderr=tr.stderr,
            execution_time_ms=tr.execution_time_ms,
            error_message=tr.error_message,
        )
        for tr in test_result_records
    ]

    return SubmissionOut(
        id=submission.id,
        student_name=submission.student_name,
        consigna_id=submission.consigna_id,
        original_filename=submission.original_filename,
        status=submission.status,
        score=submission.score,
        max_score=submission.max_score,
        feedback_llm=submission.feedback_llm,
        created_at=submission.created_at,
        source_files=result.get("source_files", []),
        cumple_consigna=result.get("cumple_consigna"),
        compilacion=compilacion,
        checks_estaticos=checks,
        tests_io=tests_io,
    )
