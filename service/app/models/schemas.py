from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Compilación
# ---------------------------------------------------------------------------

class CompilationResult(BaseModel):
    success: bool
    errors: list[str]
    warnings: list[str]


# ---------------------------------------------------------------------------
# Checks estáticos
# ---------------------------------------------------------------------------

class StaticCheckResult(BaseModel):
    descripcion: str
    passed: bool
    found: int


# ---------------------------------------------------------------------------
# Tests I/O
# ---------------------------------------------------------------------------

class TestCaseResult(BaseModel):
    descripcion: str
    passed: bool
    output: str
    error: str


# ---------------------------------------------------------------------------
# Consignas
# ---------------------------------------------------------------------------

class CasoPruebaOut(BaseModel):
    id: int
    descripcion: str
    input: str
    expected_output: str
    check_type: str
    timeout_seg: int
    points: int
    visibility: str

    model_config = {"from_attributes": True}


class CheckEstaticoOut(BaseModel):
    id: int
    descripcion: str
    pattern: str
    check_type: str
    min_count: int

    model_config = {"from_attributes": True}


class ConsignaOut(BaseModel):
    id: int
    nombre: str
    descripcion: str
    is_active: bool
    requires_tda: bool
    requires_void_pointer: bool
    requires_modularization: bool
    casos_prueba: list[CasoPruebaOut] = []
    checks_estaticos: list[CheckEstaticoOut] = []

    model_config = {"from_attributes": True}


class ConsignaListItem(BaseModel):
    """Versión liviana para el listado (sin casos de prueba)."""
    id: int
    nombre: str
    descripcion: str
    is_active: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Submissions
# ---------------------------------------------------------------------------

class TestResultOut(BaseModel):
    id: int
    test_case_id: Optional[int]
    descripcion: str = ""
    passed: bool
    points_obtained: int
    input_used: str = ""
    expected_output: str
    actual_output: str
    stdout: str
    stderr: str
    execution_time_ms: Optional[int]
    error_message: str


class SubmissionOut(BaseModel):
    id: int
    student_name: str
    consigna_id: int
    original_filename: str
    status: str
    score: Optional[int]
    max_score: Optional[int]
    feedback_llm: Optional[str]
    created_at: datetime
    source_files: list[str] = []

    # Resultados de la pipeline (se populan cuando status=completed)
    cumple_consigna: Optional[bool] = None
    compilacion: Optional[CompilationResult] = None
    checks_estaticos: list[StaticCheckResult] = []
    tests_io: list[TestResultOut] = []


# ---------------------------------------------------------------------------
# Schemas de entrada para el admin (crear / editar)
# ---------------------------------------------------------------------------

class ConsignaIn(BaseModel):
    nombre: str
    descripcion: str
    is_active: bool = True
    requires_tda: bool = False
    requires_void_pointer: bool = False
    requires_modularization: bool = False


class CasoPruebaIn(BaseModel):
    descripcion: str
    input: str
    expected_output: str = ""
    check_type: str = "contains"
    timeout_seg: int = 5
    points: int = 1
    visibility: str = "public"


class CheckEstaticoIn(BaseModel):
    descripcion: str
    pattern: str
    check_type: str = "exists"
    min_count: int = 1


# ---------------------------------------------------------------------------
# Respuesta legacy — mantenida para no romper el endpoint /analizar actual
# ---------------------------------------------------------------------------

class FeedbackResult(BaseModel):
    student_name: str
    cumple_consigna: bool
    compilacion: CompilationResult
    checks_estaticos: list[StaticCheckResult]
    tests_io: list[TestCaseResult]
    score_estimado: Optional[int] = None
