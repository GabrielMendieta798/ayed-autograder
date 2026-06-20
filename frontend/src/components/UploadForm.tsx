import { useState } from 'react'
import type { SubmissionOut, ConsignaOption } from '../types'

interface Props {
  consignas: ConsignaOption[]
  onResult: (data: SubmissionOut) => void
  onLoading: (loading: boolean) => void
}

export default function UploadForm({ consignas, onResult, onLoading }: Props) {
  const [nombreAlumno, setNombreAlumno] = useState('')
  const [consignaId, setConsignaId] = useState<number | ''>('')
  const [archivo, setArchivo] = useState<File | null>(null)
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    if (!archivo || !nombreAlumno || consignaId === '') {
      setError('Completá todos los campos antes de analizar.')
      return
    }

    const formData = new FormData()
    formData.append('archivo', archivo)
    formData.append('nombre_alumno', nombreAlumno)
    formData.append('consigna_id', String(consignaId))

    onLoading(true)
    try {
      const res = await fetch('http://localhost:8000/api/submissions/analyze', {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const data = await res.json() as { detail?: string }
        throw new Error(data.detail ?? 'Error al analizar la entrega')
      }

      const data = await res.json() as SubmissionOut
      onResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido')
      onLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="card">
        <h2>Nueva corrección</h2>

        <div className="form-group">
          <label>Nombre del alumno</label>
          <input
            type="text"
            placeholder="Ej: Juan Pérez"
            value={nombreAlumno}
            onChange={e => setNombreAlumno(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label>Consigna</label>
          <select
            value={consignaId}
            onChange={e => setConsignaId(e.target.value === '' ? '' : Number(e.target.value))}
          >
            <option value="">Seleccioná una consigna...</option>
            {consignas.map(c => (
              <option key={c.id} value={c.id}>{c.nombre}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>Archivo ZIP del alumno</label>
          <div
            className="file-input-wrapper"
            onClick={() => document.getElementById('file-input')?.click()}
          >
            <input
              id="file-input"
              type="file"
              accept=".zip,.rar"
              onChange={e => setArchivo(e.target.files?.[0] ?? null)}
            />
            <p>Hacé clic para seleccionar el archivo</p>
            {archivo && <p className="file-name">{archivo.name}</p>}
          </div>
        </div>

        {error && (
          <p style={{ color: '#e53e3e', fontSize: '0.875rem', marginBottom: '0.75rem' }}>
            {error}
          </p>
        )}

        <button type="submit" className="btn">
          Analizar entrega
        </button>
      </div>
    </form>
  )
}
