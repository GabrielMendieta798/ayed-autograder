import os
import tempfile
import shutil
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import Consigna
from app.services.zip_validator import validate_and_extract
from app.services.compiler import compile_c_files
from app.services.static_analyzer import run_static_checks
from app.services.test_runner import run_tests
from app.models.schemas import FeedbackResult

router = APIRouter()


@router.post("/analizar", response_model=FeedbackResult)
async def analizar_entrega(
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
    zip_path = os.path.join(tmp_dir, archivo.filename)

    try:
        with open(zip_path, "wb") as f:
            content = await archivo.read()
            f.write(content)

        extract_dir = os.path.join(tmp_dir, "extracted")
        os.makedirs(extract_dir)

        try:
            source_files = validate_and_extract(zip_path, extract_dir)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        compilation = compile_c_files(source_files)
        static_results = run_static_checks(source_files, consigna.checks_estaticos)
        test_results = run_tests(source_files, consigna.casos_prueba)

        cumple = (
            compilation.success
            and all(r["passed"] for r in static_results)
            and all(r["passed"] for r in test_results)
        )

        return FeedbackResult(
            student_name=nombre_alumno,
            cumple_consigna=cumple,
            compilacion=compilation,
            checks_estaticos=static_results,
            tests_io=test_results,
        )

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
