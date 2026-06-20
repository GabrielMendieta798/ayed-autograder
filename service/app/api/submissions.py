import json
import os
import shutil
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.models import Consigna, Submission, TestResult
from app.models.schemas import SubmissionOut, TestResultOut, CompilationResult, StaticCheckResult
from app.services.pipeline import run_pipeline, _build_response

router = APIRouter()


@router.post("/submissions/analyze", response_model=SubmissionOut)
async def analyze(
    archivo: UploadFile = File(...),
    consigna_id: int = Form(...),
    nombre_alumno: str = Form(...),
    db: Session = Depends(get_db),
):
    if not archivo.filename.endswith((".zip", ".rar")):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos ZIP o RAR")

    consigna = db.query(Consigna).filter(Consigna.id == consigna_id).first()
    if not consigna:
        raise HTTPException(status_code=404, detail="Consigna no encontrada")

    tmp_dir = tempfile.mkdtemp()
    try:
        zip_path = os.path.join(tmp_dir, archivo.filename)
        with open(zip_path, "wb") as f:
            f.write(await archivo.read())

        extract_dir = os.path.join(tmp_dir, "extracted")
        os.makedirs(extract_dir)

        try:
            return run_pipeline(
                db=db,
                student_name=nombre_alumno,
                consigna=consigna,
                zip_path=zip_path,
                original_filename=archivo.filename,
                extract_dir=extract_dir,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.get("/submissions/{submission_id}", response_model=SubmissionOut)
def get_submission(submission_id: int, db: Session = Depends(get_db)):
    submission = (
        db.query(Submission)
        .filter(Submission.id == submission_id)
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission no encontrada")

    consigna = db.query(Consigna).filter(Consigna.id == submission.consigna_id).first()
    test_results = (
        db.query(TestResult)
        .filter(TestResult.submission_id == submission_id)
        .all()
    )

    return _build_response(submission, test_results, consigna)
