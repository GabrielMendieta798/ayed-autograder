export interface CompilationResult {
  success: boolean
  errors: string[]
  warnings: string[]
}

export interface StaticCheckResult {
  descripcion: string
  passed: boolean
  found: number
}

export interface TestResultOut {
  id: number
  test_case_id: number | null
  descripcion: string
  passed: boolean
  points_obtained: number
  input_used: string
  expected_output: string
  actual_output: string
  stdout: string
  stderr: string
  execution_time_ms: number | null
  error_message: string
}

export interface SubmissionOut {
  id: number
  student_name: string
  consigna_id: number
  original_filename: string
  status: string
  score: number | null
  max_score: number | null
  feedback_llm: string | null
  created_at: string
  source_files: string[]
  cumple_consigna: boolean | null
  compilacion: CompilationResult | null
  checks_estaticos: StaticCheckResult[]
  tests_io: TestResultOut[]
}

export interface ConsignaOption {
  id: number
  nombre: string
  descripcion: string
  is_active: boolean
}

export interface CasoPruebaOut {
  id: number
  descripcion: string
  input: string
  expected_output: string
  check_type: string
  timeout_seg: number
  points: number
  visibility: string
}

export interface CheckEstaticoOut {
  id: number
  descripcion: string
  pattern: string
  check_type: string
  min_count: number
}

export interface ConsignaDetail {
  id: number
  nombre: string
  descripcion: string
  is_active: boolean
  requires_tda: boolean
  requires_void_pointer: boolean
  requires_modularization: boolean
  casos_prueba: CasoPruebaOut[]
  checks_estaticos: CheckEstaticoOut[]
}
