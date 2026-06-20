"""
Carga la consigna demo "Calculadora básica en C" en la base de datos.
Ejecutar desde la carpeta service/ con:
    poetry run python ../demo-consigna-calculadora/seed_demo.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "service"))

from app.models.database import SessionLocal, engine, Base
from app.models import models  # noqa: F401
from app.models.models import Consigna, CasoPrueba, CheckEstatico

Base.metadata.create_all(bind=engine)
db = SessionLocal()

existing = db.query(Consigna).filter(Consigna.nombre == "TP Demo - Calculadora básica en C").first()
if existing:
    db.delete(existing)
    db.commit()
    print("Consigna anterior eliminada.")

consigna = Consigna(
    nombre="TP Demo - Calculadora básica en C",
    descripcion=(
        "El programa lee dos enteros y un operador (+, -, *, /) en una sola línea "
        "(formato: A op B) e imprime el resultado. "
        "Para división por cero debe imprimir exactamente: Error: division por cero"
    ),
)

consigna.checks_estaticos = [
    CheckEstatico(
        descripcion="Usa scanf para leer la entrada",
        pattern=r"scanf\s*\(",
        check_type="exists",
    ),
    CheckEstatico(
        descripcion="Usa printf para imprimir el resultado",
        pattern=r"printf\s*\(",
        check_type="exists",
    ),
]

consigna.casos_prueba = [
    CasoPrueba(
        descripcion="Suma básica: 3 + 5 = 8",
        input="3 + 5\n",
        expected_output="8",
        check_type="contains",
        timeout_seg=5,
        points=2,
        visibility="public",
    ),
    CasoPrueba(
        descripcion="Resta: 10 - 3 = 7",
        input="10 - 3\n",
        expected_output="7",
        check_type="contains",
        timeout_seg=5,
        points=2,
        visibility="public",
    ),
    CasoPrueba(
        descripcion="Multiplicación: 4 * 6 = 24",
        input="4 * 6\n",
        expected_output="24",
        check_type="contains",
        timeout_seg=5,
        points=2,
        visibility="public",
    ),
    CasoPrueba(
        descripcion="División exacta: 15 / 3 = 5",
        input="15 / 3\n",
        expected_output="5",
        check_type="contains",
        timeout_seg=5,
        points=2,
        visibility="public",
    ),
    CasoPrueba(
        descripcion="División por cero: 7 / 0",
        input="7 / 0\n",
        expected_output="Error: division por cero",
        check_type="contains",
        timeout_seg=5,
        points=3,
        visibility="public",
    ),
]

db.add(consigna)
db.commit()
db.close()
print(f"Consigna '{consigna.nombre}' cargada exitosamente.")
print("Checks estáticos: 2")
print("Casos de prueba: 5 (puntaje máximo: 11)")
