from dataclasses import dataclass, field


@dataclass(frozen=True)
class WorkerTestCase:
    name: str
    input: str = ""
    expected_output: str = ""
    check_type: str = "contains"
    timeout_seg: int = 5
    points: int = 1

    @property
    def descripcion(self) -> str:
        return self.name


@dataclass(frozen=True)
class WorkerStaticCheck:
    name: str
    pattern: str
    check_type: str = "exists"
    min_count: int = 1

    @property
    def descripcion(self) -> str:
        return self.name


@dataclass(frozen=True)
class GradeJob:
    job_id: str
    archive_path: str
    tests: tuple[WorkerTestCase, ...] = ()
    static_checks: tuple[WorkerStaticCheck, ...] = ()


@dataclass(frozen=True)
class CompilationEvidence:
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class TestEvidence:
    name: str
    passed: bool
    input: str
    expected_output: str
    actual_output: str
    stderr: str = ""
    error: str = ""
    points_obtained: int = 0
    points_maximum: int = 0


@dataclass(frozen=True)
class StaticCheckEvidence:
    name: str
    passed: bool
    found: int


@dataclass(frozen=True)
class ScoreEvidence:
    obtained: int
    maximum: int


@dataclass
class GradeContext:
    job: GradeJob
    source_files: list[str] = field(default_factory=list)
    compilation: CompilationEvidence | None = None
    tests: list[TestEvidence] = field(default_factory=list)
    static_checks: list[StaticCheckEvidence] = field(default_factory=list)
    score: ScoreEvidence | None = None
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GradeEvidence:
    job_id: str
    status: str
    compilation: CompilationEvidence
    tests: tuple[TestEvidence, ...]
    static_analysis: tuple[StaticCheckEvidence, ...]
    score: ScoreEvidence
    errors: tuple[str, ...]
    duration_ms: int
