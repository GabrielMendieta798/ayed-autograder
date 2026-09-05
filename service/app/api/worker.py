import os
import shutil
import tempfile
from dataclasses import asdict

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import ValidationError

from app.worker.pipeline import run_worker_grade_job
from app.worker.schemas import GradeRequest, GradeResult
from app.worker.domain import GradeJob, WorkerStaticCheck, WorkerTestCase


router = APIRouter()


@router.post("/grade", response_model=GradeResult)
async def grade(
    archivo: UploadFile = File(...),
    config: str = Form(...),
):
    if not archivo.filename or not archivo.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos ZIP")

    try:
        request = GradeRequest.model_validate_json(config)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    tmp_dir = tempfile.mkdtemp(prefix="autocorrector-upload-")
    try:
        archive_path = os.path.join(tmp_dir, "submission.zip")
        with open(archive_path, "wb") as destination:
            shutil.copyfileobj(archivo.file, destination)
        try:
            job = GradeJob(
                job_id=request.job_id,
                archive_path=archive_path,
                tests=tuple(
                    WorkerTestCase(**test.model_dump()) for test in request.tests
                ),
                static_checks=tuple(
                    WorkerStaticCheck(**check.model_dump())
                    for check in request.static_checks
                ),
            )
            evidence = run_worker_grade_job(job)
            result = asdict(evidence)
            result["static_analysis"] = {"checks": result["static_analysis"]}
            return GradeResult.model_validate(result)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
