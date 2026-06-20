from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import Consigna
from app.models.schemas import ConsignaOut, ConsignaListItem

router = APIRouter()


@router.get("/consignas", response_model=list[ConsignaListItem])
def listar_consignas(db: Session = Depends(get_db)):
    return db.query(Consigna).filter(Consigna.is_active == True).order_by(Consigna.nombre).all()


@router.get("/consignas/{consigna_id}", response_model=ConsignaOut)
def obtener_consigna(consigna_id: int, db: Session = Depends(get_db)):
    consigna = db.query(Consigna).filter(Consigna.id == consigna_id).first()
    if not consigna:
        raise HTTPException(status_code=404, detail="Consigna no encontrada")
    return consigna
