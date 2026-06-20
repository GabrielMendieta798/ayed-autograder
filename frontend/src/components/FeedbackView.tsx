import type { SubmissionOut, TestResultOut } from '../types'

interface Props {
  result: SubmissionOut
  onReset: () => void
}

function PassBadge({ passed }: { passed: boolean }) {
  return (
    <span className={`status-badge ${passed ? 'status-ok' : 'status-error'}`}>
      {passed ? '✓' : '✗'}
    </span>
  )
}

function FileTag({ name }: { name: string }) {
  const isHeader = name.endsWith('.h')
  return (
    <span style={{
      display: 'inline-block',
      padding: '0.15rem 0.5rem',
      borderRadius: '4px',
      fontSize: '0.8rem',
      fontFamily: 'monospace',
      background: isHeader ? '#ebf4ff' : '#f0fff4',
      color: isHeader ? '#2b6cb0' : '#276749',
      border: `1px solid ${isHeader ? '#bee3f8' : '#9ae6b4'}`,
      marginRight: '0.4rem',
      marginBottom: '0.4rem',
    }}>
      {name}
    </span>
  )
}

function TestDetail({ test }: { test: TestResultOut }) {
  const showDetail = !test.passed || test.input_used || test.expected_output

  return (
    <div style={{
      border: `1px solid ${test.passed ? '#9ae6b4' : '#feb2b2'}`,
      borderRadius: '6px',
      marginBottom: '0.75rem',
      overflow: 'hidden',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        padding: '0.6rem 0.75rem',
        background: test.passed ? '#f0fff4' : '#fff5f5',
      }}>
        <PassBadge passed={test.passed} />
        <span style={{ flex: 1, fontWeight: 500 }}>{test.descripcion}</span>
        {test.points_obtained > 0 && (
          <span style={{ color: '#276749', fontSize: '0.85rem' }}>
            +{test.points_obtained} pts
          </span>
        )}
        {!test.passed && test.points_obtained === 0 && (
          <span style={{ color: '#9b2c2c', fontSize: '0.85rem' }}>0 pts</span>
        )}
        {test.execution_time_ms != null && (
          <span style={{ color: '#718096', fontSize: '0.8rem' }}>{test.execution_time_ms} ms</span>
        )}
      </div>

      {showDetail && (
        <div style={{ padding: '0.6rem 0.75rem', fontSize: '0.85rem' }}>
          {test.input_used && (
            <div style={{ marginBottom: '0.5rem' }}>
              <div style={{ color: '#718096', marginBottom: '0.2rem' }}>Input</div>
              <pre style={{ margin: 0, background: '#f7fafc', padding: '0.4rem 0.6rem', borderRadius: '4px', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                {test.input_used}
              </pre>
            </div>
          )}
          {test.expected_output && (
            <div style={{ marginBottom: '0.5rem' }}>
              <div style={{ color: '#718096', marginBottom: '0.2rem' }}>Output esperado</div>
              <pre style={{ margin: 0, background: '#f7fafc', padding: '0.4rem 0.6rem', borderRadius: '4px', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                {test.expected_output}
              </pre>
            </div>
          )}
          {!test.passed && (
            <div style={{ marginBottom: test.error_message ? '0.5rem' : 0 }}>
              <div style={{ color: '#718096', marginBottom: '0.2rem' }}>Output obtenido</div>
              <pre style={{ margin: 0, background: '#fff5f5', padding: '0.4rem 0.6rem', borderRadius: '4px', whiteSpace: 'pre-wrap', wordBreak: 'break-all', color: '#c53030' }}>
                {test.actual_output || '(sin output)'}
              </pre>
            </div>
          )}
          {test.error_message && (
            <div style={{ color: '#e53e3e', fontSize: '0.8rem', marginTop: '0.3rem' }}>
              {test.error_message}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function FeedbackView({ result, onReset }: Props) {
  const {
    student_name, cumple_consigna, compilacion, checks_estaticos,
    tests_io, score, max_score, feedback_llm, source_files, original_filename,
  } = result

  const scorePercent = max_score && max_score > 0
    ? Math.round(((score ?? 0) / max_score) * 100)
    : null

  const staticPassed = checks_estaticos.filter(c => c.passed).length
  const testsPassed = tests_io.filter(t => t.passed).length

  return (
    <>
      {/* Resumen */}
      <div className="card">
        <h2>Resultado — {student_name}</h2>
        <p style={{ color: '#718096', fontSize: '0.85rem', marginBottom: '1rem' }}>
          {original_filename}
        </p>

        <div className="grid-2" style={{ marginBottom: '1rem' }}>
          {max_score != null && max_score > 0 ? (
            <div className="stat-box">
              <div className="stat-num">{score ?? 0}<span style={{ fontSize: '1.2rem', color: '#718096' }}>/{max_score}</span></div>
              <div className="stat-label">Puntos{scorePercent != null ? ` (${scorePercent}%)` : ''}</div>
            </div>
          ) : (
            <div className="stat-box">
              <div className="stat-num">{staticPassed}/{checks_estaticos.length}</div>
              <div className="stat-label">Checks estáticos</div>
            </div>
          )}
          <div className="stat-box">
            <div className="stat-num">{testsPassed}/{tests_io.length}</div>
            <div className="stat-label">Tests pasados</div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <span className={`status-badge ${compilacion?.success ? 'status-ok' : 'status-error'}`}>
            {compilacion?.success ? '✓ Compiló' : '✗ No compiló'}
          </span>
          <span className={`status-badge ${cumple_consigna ? 'status-ok' : 'status-error'}`}>
            {cumple_consigna ? '✓ Cumple la consigna' : '✗ No cumple la consigna'}
          </span>
          {compilacion && compilacion.warnings.length > 0 && (
            <span className="status-badge status-warning">
              ⚠ {compilacion.warnings.length} warning{compilacion.warnings.length > 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      {/* Archivos */}
      {source_files.length > 0 && (
        <div className="card">
          <h2>Archivos entregados</h2>
          <div style={{ marginTop: '0.5rem' }}>
            {source_files.map(f => <FileTag key={f} name={f} />)}
          </div>
        </div>
      )}

      {/* Compilación */}
      {compilacion && (compilacion.errors.length > 0 || compilacion.warnings.length > 0) && (
        <div className="card">
          <h2>Compilación</h2>
          {compilacion.errors.length > 0 && (
            <>
              <p className="section-title">Errores</p>
              <div className="code-block" style={{ marginBottom: '1rem' }}>
                {compilacion.errors.map((e, i) => (
                  <div key={i} className="line-error">{e}</div>
                ))}
              </div>
            </>
          )}
          {compilacion.warnings.length > 0 && (
            <>
              <p className="section-title">Warnings</p>
              <div className="code-block">
                {compilacion.warnings.map((w, i) => (
                  <div key={i} className="line-warning">{w}</div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* Checks estáticos */}
      {checks_estaticos.length > 0 && (
        <div className="card">
          <h2>Análisis estático del código</h2>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
            <tbody>
              {checks_estaticos.map((c, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #e2e8f0' }}>
                  <td style={{ padding: '0.5rem 0.25rem', width: '2rem' }}>
                    <PassBadge passed={c.passed} />
                  </td>
                  <td style={{ padding: '0.5rem 0.25rem' }}>{c.descripcion}</td>
                  <td style={{ padding: '0.5rem 0.25rem', color: '#718096', textAlign: 'right' }}>
                    {c.found} ocurrencia{c.found !== 1 ? 's' : ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Tests I/O */}
      {tests_io.length > 0 && (
        <div className="card">
          <h2>Tests I/O</h2>
          <div style={{ marginTop: '0.5rem' }}>
            {tests_io.map(t => <TestDetail key={t.id} test={t} />)}
          </div>
        </div>
      )}

      {/* Feedback LLM */}
      {feedback_llm && (
        <div className="card">
          <h2>Feedback del corrector</h2>
          <div style={{ whiteSpace: 'pre-wrap', fontSize: '0.9rem', lineHeight: 1.6, color: '#2d3748' }}>
            {feedback_llm}
          </div>
        </div>
      )}

      <button className="btn btn-secondary" onClick={onReset}>
        Analizar otra entrega
      </button>
    </>
  )
}
