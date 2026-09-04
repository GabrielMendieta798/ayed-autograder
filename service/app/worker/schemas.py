from typing import Literal

from pydantic import BaseModel, Field


class WorkerTestCase(BaseModel):
    name: str
    input: str = ""
    expected_output: str = ""
    check_type: Literal["exitcode", "contains", "exact"] = "contains"
    timeout_seg: int = Field(default=5, ge=1, le=60)
    points: int = Field(default=1, ge=0)

    @property
    def descripcion(self) -> str:
        return self.name


class WorkerStaticCheck(BaseModel):
    name: str
    pattern: str
    check_type: Literal["exists", "count_gte"] = "exists"
    min_count: int = Field(default=1, ge=1)

    @property
    def descripcion(self) -> str:
        return self.name


class GradeRequest(BaseModel):
    job_id: str = Field(min_length=1, max_length=200)
    tests: list[WorkerTestCase] = Field(default_factory=list)
    static_checks: list[WorkerStaticCheck] = Field(default_factory=list)


class CompilationResult(BaseModel):
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class TestCaseResult(BaseModel):
    name: str
    passed: bool
    input: str
    expected_output: str
    actual_output: str
    stderr: str = ""
    error: str = ""
    points_obtained: int = 0
    points_maximum: int = 0


class StaticCheckResult(BaseModel):
    name: str
    passed: bool
    found: int


class StaticAnalysisResult(BaseModel):
    checks: list[StaticCheckResult] = Field(default_factory=list)


class ScoreResult(BaseModel):
    obtained: int
    maximum: int


class GradeResult(BaseModel):
    job_id: str
    status: Literal["completed", "failed"]
    compilation: CompilationResult
    tests: list[TestCaseResult]
    static_analysis: StaticAnalysisResult
    score: ScoreResult
    errors: list[str] = Field(default_factory=list)
    duration_ms: int
