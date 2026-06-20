from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.models import CasoPrueba, CheckEstatico, Consigna
from app.models.schemas import (
    CasoPruebaIn,
    CasoPruebaOut,
    CheckEstaticoIn,
    CheckEstaticoOut,
    ConsignaIn,
    ConsignaOut,
)

router = APIRouter(prefix="/admin")


# ---------------------------------------------------------------------------
# Consignas
# ---------------------------------------------------------------------------

@router.post("/consignas", response_model=ConsignaOut, status_code=201)
def crear_consigna(data: ConsignaIn, db: Session = Depends(get_db)):
    consigna = Consigna(**data.model_dump())
    db.add(consigna)
    db.commit()
    db.refresh(consigna)
    return consigna


@router.put("/consignas/{consigna_id}", response_model=ConsignaOut)
def editar_consigna(consigna_id: int, data: ConsignaIn, db: Session = Depends(get_db)):
    consigna = db.query(Consigna).filter(Consigna.id == consigna_id).first()
    if not consigna:
        raise HTTPException(status_code=404, detail="Consigna no encontrada")
    for field, value in data.model_dump().items():
        setattr(consigna, field, value)
    db.commit()
    db.refresh(consigna)
    return consigna


@router.delete("/consignas/{consigna_id}", status_code=204)
def eliminar_consigna(consigna_id: int, db: Session = Depends(get_db)):
    consigna = db.query(Consigna).filter(Consigna.id == consigna_id).first()
    if not consigna:
        raise HTTPException(status_code=404, detail="Consigna no encontrada")
    db.delete(consigna)
    db.commit()


# ---------------------------------------------------------------------------
# Casos de prueba
# ---------------------------------------------------------------------------

@router.post("/consignas/{consigna_id}/casos", response_model=CasoPruebaOut, status_code=201)
def agregar_caso(consigna_id: int, data: CasoPruebaIn, db: Session = Depends(get_db)):
    if not db.query(Consigna).filter(Consigna.id == consigna_id).first():
        raise HTTPException(status_code=404, detail="Consigna no encontrada")
    caso = CasoPrueba(consigna_id=consigna_id, **data.model_dump())
    db.add(caso)
    db.commit()
    db.refresh(caso)
    return caso


@router.put("/casos/{caso_id}", response_model=CasoPruebaOut)
def editar_caso(caso_id: int, data: CasoPruebaIn, db: Session = Depends(get_db)):
    caso = db.query(CasoPrueba).filter(CasoPrueba.id == caso_id).first()
    if not caso:
        raise HTTPException(status_code=404, detail="Caso de prueba no encontrado")
    for field, value in data.model_dump().items():
        setattr(caso, field, value)
    db.commit()
    db.refresh(caso)
    return caso


@router.delete("/casos/{caso_id}", status_code=204)
def eliminar_caso(caso_id: int, db: Session = Depends(get_db)):
    caso = db.query(CasoPrueba).filter(CasoPrueba.id == caso_id).first()
    if not caso:
        raise HTTPException(status_code=404, detail="Caso de prueba no encontrado")
    db.delete(caso)
    db.commit()


# ---------------------------------------------------------------------------
# Checks estáticos
# ---------------------------------------------------------------------------

@router.post("/consignas/{consigna_id}/checks", response_model=CheckEstaticoOut, status_code=201)
def agregar_check(consigna_id: int, data: CheckEstaticoIn, db: Session = Depends(get_db)):
    if not db.query(Consigna).filter(Consigna.id == consigna_id).first():
        raise HTTPException(status_code=404, detail="Consigna no encontrada")
    check = CheckEstatico(consigna_id=consigna_id, **data.model_dump())
    db.add(check)
    db.commit()
    db.refresh(check)
    return check


@router.put("/checks/{check_id}", response_model=CheckEstaticoOut)
def editar_check(check_id: int, data: CheckEstaticoIn, db: Session = Depends(get_db)):
    check = db.query(CheckEstatico).filter(CheckEstatico.id == check_id).first()
    if not check:
        raise HTTPException(status_code=404, detail="Check estático no encontrado")
    for field, value in data.model_dump().items():
        setattr(check, field, value)
    db.commit()
    db.refresh(check)
    return check


@router.delete("/checks/{check_id}", status_code=204)
def eliminar_check(check_id: int, db: Session = Depends(get_db)):
    check = db.query(CheckEstatico).filter(CheckEstatico.id == check_id).first()
    if not check:
        raise HTTPException(status_code=404, detail="Check estático no encontrado")
    db.delete(check)
    db.commit()
