"""
Carga la consigna TP2 con sus checks estáticos y casos de prueba.
Ejecutar desde la carpeta service/ con:
    poetry run python seed.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.models.database import SessionLocal, engine, Base
from app.models import models  # noqa: F401
from app.models.models import Consigna, CasoPrueba, CheckEstatico

Base.metadata.create_all(bind=engine)
db = SessionLocal()

existing = db.query(Consigna).filter(Consigna.nombre == "TP2 - Pila y Cola void").first()
if existing:
    db.delete(existing)
    db.commit()

consigna = Consigna(
    nombre="TP2 - Pila y Cola void",
    descripcion=(
        "El programa deberá administrar como mínimo 3 estructuras propias, bajo el paradigma de TDA. "
        "Deberá utilizar por lo menos una pila void y una cola void. "
        "El menú debe permitir: apilar, desapilar, ver tope, encolar, desencolar, ver frente. "
        "Es requisito utilizar funciones callback en todo su desarrollo."
    ),
)

consigna.checks_estaticos = [
    CheckEstatico(
        descripcion="Usa puntero void (void*)",
        pattern=r"void\s*\*",
        check_type="exists",
    ),
    CheckEstatico(
        descripcion="Usa funciones callback (puntero a función)",
        pattern=r"\(\s*\*\s*\w+\s*\)\s*\(",
        check_type="exists",
    ),
    CheckEstatico(
        descripcion="Define al menos 3 estructuras (typedef struct)",
        pattern=r"typedef\s+struct",
        check_type="count_gte",
        min_count=3,
    ),
]

# Menú fijo esperado:
# 1. Apilar   2. Desapilar   3. Ver tope
# 4. Encolar  5. Desencolar  6. Ver frente   0. Salir
#
# Todos los casos asumen que el primer campo pedido al apilar/encolar
# es el nombre del elemento (string). El alumno puede tener más campos,
# pero "nombre" debe ser el primero para que los tests de contenido funcionen.

consigna.casos_prueba = [
    CasoPrueba(
        descripcion="El programa termina limpiamente con opción 0",
        input="0\n",
        expected_output="",
        check_type="exitcode",
        points=1,
    ),
    CasoPrueba(
        descripcion="Apilar un elemento y verlo en el tope (opción 3)",
        input="1\nJuan\n3\n0\n",
        expected_output="Juan",
        check_type="contains",
        points=2,
    ),
    CasoPrueba(
        descripcion="LIFO: el último apilado aparece primero en el tope",
        input="1\nJuan\n1\nPedro\n3\n0\n",
        expected_output="Pedro",
        check_type="contains",
        points=2,
    ),
    CasoPrueba(
        descripcion="Encolar un elemento y verlo al frente (opción 6)",
        input="4\nJuan\n6\n0\n",
        expected_output="Juan",
        check_type="contains",
        points=2,
    ),
    CasoPrueba(
        descripcion="FIFO: el primero encolado aparece primero al frente",
        input="4\nJuan\n4\nPedro\n6\n0\n",
        expected_output="Juan",
        check_type="contains",
        points=2,
    ),
    CasoPrueba(
        descripcion="Desapilar con pila vacía no genera crash",
        input="2\n0\n",
        expected_output="",
        check_type="exitcode",
        points=1,
    ),
    CasoPrueba(
        descripcion="Desencolar con cola vacía no genera crash",
        input="5\n0\n",
        expected_output="",
        check_type="exitcode",
        points=1,
    ),
]

db.add(consigna)
db.commit()
db.close()
print("Consigna 'TP2 - Pila y Cola void' cargada exitosamente.")
