from datetime import datetime
from typing import Optional
from sqlalchemy import ForeignKey, String, Text, Integer, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.database import Base


class Consigna(Base):
    __tablename__ = "consignas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_tda: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_void_pointer: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_modularization: Mapped[bool] = mapped_column(Boolean, default=False)

    casos_prueba: Mapped[list["CasoPrueba"]] = relationship(
        back_populates="consigna", cascade="all, delete-orphan"
    )
    checks_estaticos: Mapped[list["CheckEstatico"]] = relationship(
        back_populates="consigna", cascade="all, delete-orphan"
    )
    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="consigna", cascade="all, delete-orphan"
    )


class CasoPrueba(Base):
    __tablename__ = "casos_prueba"

    id: Mapped[int] = mapped_column(primary_key=True)
    consigna_id: Mapped[int] = mapped_column(ForeignKey("consignas.id"))
    descripcion: Mapped[str] = mapped_column(String(200))
    input: Mapped[str] = mapped_column(Text)
    expected_output: Mapped[str] = mapped_column(Text, default="")
    # "exitcode" → solo verifica que salga con código 0
    # "contains" → stdout contiene expected_output (case-insensitive)
    # "exact"    → stdout coincide exactamente con expected_output
    check_type: Mapped[str] = mapped_column(String(20), default="contains")
    timeout_seg: Mapped[int] = mapped_column(Integer, default=5)
    points: Mapped[int] = mapped_column(Integer, default=1)
    # "public" → el profesor ve input/output esperado antes de analizar
    # "hidden" → solo se muestra si el test pasa o falla
    visibility: Mapped[str] = mapped_column(String(20), default="public")

    consigna: Mapped["Consigna"] = relationship(back_populates="casos_prueba")


class CheckEstatico(Base):
    __tablename__ = "checks_estaticos"

    id: Mapped[int] = mapped_column(primary_key=True)
    consigna_id: Mapped[int] = mapped_column(ForeignKey("consignas.id"))
    descripcion: Mapped[str] = mapped_column(String(200))
    pattern: Mapped[str] = mapped_column(String(500))
    # "exists"    → el patrón aparece al menos una vez
    # "count_gte" → el patrón aparece al menos min_count veces
    check_type: Mapped[str] = mapped_column(String(20), default="exists")
    min_count: Mapped[int] = mapped_column(Integer, default=1)

    consigna: Mapped["Consigna"] = relationship(back_populates="checks_estaticos")


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_name: Mapped[str] = mapped_column(String(200))
    consigna_id: Mapped[int] = mapped_column(ForeignKey("consignas.id"))
    original_filename: Mapped[str] = mapped_column(String(200))
    # pending | running | completed | failed
    status: Mapped[str] = mapped_column(String(20), default="pending")
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    feedback_llm: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    consigna: Mapped["Consigna"] = relationship(back_populates="submissions")
    test_results: Mapped[list["TestResult"]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )


class TestResult(Base):
    __tablename__ = "test_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"))
    test_case_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("casos_prueba.id"), nullable=True
    )
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    points_obtained: Mapped[int] = mapped_column(Integer, default=0)
    stdout: Mapped[str] = mapped_column(Text, default="")
    stderr: Mapped[str] = mapped_column(Text, default="")
    expected_output: Mapped[str] = mapped_column(Text, default="")
    actual_output: Mapped[str] = mapped_column(Text, default="")
    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, default="")

    submission: Mapped["Submission"] = relationship(back_populates="test_results")
    test_case: Mapped[Optional["CasoPrueba"]] = relationship()
