import { useState, useEffect } from 'react'
import UploadForm from './components/UploadForm'
import FeedbackView from './components/FeedbackView'
import AdminView from './components/AdminView'
import type { SubmissionOut, ConsignaOption } from './types'

type Screen = 'corrector' | 'admin'

export default function App() {
  const [screen, setScreen] = useState<Screen>('corrector')
  const [result, setResult] = useState<SubmissionOut | null>(null)
  const [loading, setLoading] = useState(false)
  const [consignas, setConsignas] = useState<ConsignaOption[]>([])

  function loadConsignas() {
    fetch('http://localhost:8000/api/consignas')
      .then(r => r.json())
      .then((data: ConsignaOption[]) => setConsignas(data))
      .catch(() => setConsignas([]))
  }

  useEffect(() => { loadConsignas() }, [])

  // Al volver del admin, refrescar las consignas por si se agregaron nuevas
  function handleScreenChange(s: Screen) {
    setScreen(s)
    if (s === 'corrector') loadConsignas()
  }

  function handleResult(data: SubmissionOut) {
    setResult(data)
    setLoading(false)
  }

  function handleReset() {
    setResult(null)
  }

  return (
    <>
      <header className="header">
        <div>
          <h1>Corrector Automático AED</h1>
          <span>Universidad Nacional de Lanús</span>
        </div>
        <nav style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={() => handleScreenChange('corrector')}
            style={{ background: screen === 'corrector' ? '#fff' : 'transparent', color: screen === 'corrector' ? '#2b6cb0' : '#fff', border: '1px solid #fff', borderRadius: '6px', padding: '0.3rem 0.8rem', cursor: 'pointer', fontSize: '0.9rem', fontWeight: screen === 'corrector' ? 600 : 400 }}
          >
            Corrector
          </button>
          <button
            onClick={() => handleScreenChange('admin')}
            style={{ background: screen === 'admin' ? '#fff' : 'transparent', color: screen === 'admin' ? '#2b6cb0' : '#fff', border: '1px solid #fff', borderRadius: '6px', padding: '0.3rem 0.8rem', cursor: 'pointer', fontSize: '0.9rem', fontWeight: screen === 'admin' ? 600 : 400 }}
          >
            Admin
          </button>
        </nav>
      </header>

      {screen === 'admin' ? (
        <AdminView />
      ) : (
        <div className="container">
          {loading && (
            <div className="card loading">
              <div className="spinner" />
              <p>Analizando entrega...</p>
              <p style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>Compilando y ejecutando tests</p>
            </div>
          )}

          {!loading && !result && (
            <UploadForm consignas={consignas} onResult={handleResult} onLoading={setLoading} />
          )}

          {!loading && result && (
            <FeedbackView result={result} onReset={handleReset} />
          )}
        </div>
      )}
    </>
  )
}
