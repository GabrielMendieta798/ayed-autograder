import { useState, useEffect } from 'react'
import type { ConsignaDetail, CasoPruebaOut, CheckEstaticoOut } from '../types'

const API = 'http://localhost:8000/api'

// ---------------------------------------------------------------------------
// Formulario: Consigna
// ---------------------------------------------------------------------------

interface ConsignaFormData {
  nombre: string
  descripcion: string
  is_active: boolean
  requires_tda: boolean
  requires_void_pointer: boolean
  requires_modularization: boolean
}

const emptyConsigna = (): ConsignaFormData => ({
  nombre: '',
  descripcion: '',
  is_active: true,
  requires_tda: false,
  requires_void_pointer: false,
  requires_modularization: false,
})

// ---------------------------------------------------------------------------
// Formulario: Caso de prueba
// ---------------------------------------------------------------------------

interface CasoFormData {
  descripcion: string
  input: string
  expected_output: string
  check_type: string
  timeout_seg: number
  points: number
  visibility: string
}

const emptyCaso = (): CasoFormData => ({
  descripcion: '',
  input: '',
  expected_output: '',
  check_type: 'contains',
  timeout_seg: 5,
  points: 1,
  visibility: 'public',
})

// ---------------------------------------------------------------------------
// Formulario: Check estático
// ---------------------------------------------------------------------------

interface CheckFormData {
  descripcion: string
  pattern: string
  check_type: string
  min_count: number
}

const emptyCheck = (): CheckFormData => ({
  descripcion: '',
  pattern: '',
  check_type: 'exists',
  min_count: 1,
})

// ---------------------------------------------------------------------------
// Panel de casos de prueba
// ---------------------------------------------------------------------------

function CasosPanel({ consignaId, casos, onRefresh }: {
  consignaId: number
  casos: CasoPruebaOut[]
  onRefresh: () => void
}) {
  const [form, setForm] = useState<CasoFormData>(emptyCaso())
  const [editingId, setEditingId] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)

  function startEdit(c: CasoPruebaOut) {
    setEditingId(c.id)
    setForm({ descripcion: c.descripcion, input: c.input, expected_output: c.expected_output, check_type: c.check_type, timeout_seg: c.timeout_seg, points: c.points, visibility: c.visibility })
  }

  function cancelEdit() {
    setEditingId(null)
    setForm(emptyCaso())
  }

  async function save() {
    setSaving(true)
    try {
      const url = editingId
        ? `${API}/admin/casos/${editingId}`
        : `${API}/admin/consignas/${consignaId}/casos`
      const method = editingId ? 'PUT' : 'POST'
      const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form) })
      if (!res.ok) throw new Error(await res.text())
      setForm(emptyCaso())
      setEditingId(null)
      onRefresh()
    } finally {
      setSaving(false)
    }
  }

  async function remove(id: number) {
    if (!confirm('¿Eliminar este caso de prueba?')) return
    await fetch(`${API}/admin/casos/${id}`, { method: 'DELETE' })
    onRefresh()
  }

  const isFormValid = form.descripcion.trim() && (form.check_type === 'exitcode' || form.expected_output.trim())

  return (
    <div>
      <h3 style={{ marginBottom: '0.75rem' }}>Casos de prueba I/O</h3>

      {casos.length === 0 && <p style={{ color: '#718096', fontSize: '0.9rem' }}>No hay casos de prueba.</p>}

      {casos.map(c => (
        <div key={c.id} style={{ border: '1px solid #e2e8f0', borderRadius: '6px', padding: '0.75rem', marginBottom: '0.5rem', background: '#f7fafc' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <strong>{c.descripcion}</strong>
              <span style={{ marginLeft: '0.5rem', fontSize: '0.8rem', color: '#718096' }}>[{c.check_type}] {c.points} pt{c.points !== 1 ? 's' : ''}</span>
            </div>
            <div style={{ display: 'flex', gap: '0.4rem' }}>
              <button className="btn btn-secondary" style={{ padding: '0.2rem 0.6rem', fontSize: '0.8rem' }} onClick={() => startEdit(c)}>Editar</button>
              <button className="btn" style={{ padding: '0.2rem 0.6rem', fontSize: '0.8rem', background: '#fc8181', color: '#fff' }} onClick={() => remove(c.id)}>Eliminar</button>
            </div>
          </div>
          {c.input && (
            <pre style={{ margin: '0.4rem 0 0', fontSize: '0.78rem', background: '#edf2f7', padding: '0.3rem 0.5rem', borderRadius: '4px', whiteSpace: 'pre-wrap' }}>
              input: {c.input}
            </pre>
          )}
          {c.expected_output && (
            <pre style={{ margin: '0.3rem 0 0', fontSize: '0.78rem', background: '#edf2f7', padding: '0.3rem 0.5rem', borderRadius: '4px', whiteSpace: 'pre-wrap' }}>
              esperado: {c.expected_output}
            </pre>
          )}
        </div>
      ))}

      <div style={{ border: '1px dashed #cbd5e0', borderRadius: '6px', padding: '0.75rem', marginTop: '1rem' }}>
        <strong style={{ fontSize: '0.9rem' }}>{editingId ? 'Editar caso' : 'Agregar caso de prueba'}</strong>
        <div style={{ display: 'grid', gap: '0.5rem', marginTop: '0.5rem' }}>
          <input className="input" placeholder="Descripción (ej: 'Suma dos números')" value={form.descripcion} onChange={e => setForm({ ...form, descripcion: e.target.value })} />
          <textarea className="input" placeholder="Input (lo que se le pasa por stdin al programa)" rows={2} style={{ fontFamily: 'monospace', fontSize: '0.85rem' }} value={form.input} onChange={e => setForm({ ...form, input: e.target.value })} />
          <select className="input" value={form.check_type} onChange={e => setForm({ ...form, check_type: e.target.value })}>
            <option value="contains">contains — la salida contiene el texto (sin distinción de mayúsculas)</option>
            <option value="exact">exact — la salida coincide exactamente</option>
            <option value="exitcode">exitcode — solo verifica que el programa no crashee</option>
          </select>
          {form.check_type !== 'exitcode' && (
            <textarea className="input" placeholder="Output esperado" rows={2} style={{ fontFamily: 'monospace', fontSize: '0.85rem' }} value={form.expected_output} onChange={e => setForm({ ...form, expected_output: e.target.value })} />
          )}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem' }}>
            <label style={{ fontSize: '0.85rem' }}>
              Puntos
              <input className="input" type="number" min={0} value={form.points} onChange={e => setForm({ ...form, points: +e.target.value })} style={{ marginTop: '0.2rem' }} />
            </label>
            <label style={{ fontSize: '0.85rem' }}>
              Timeout (seg)
              <input className="input" type="number" min={1} max={30} value={form.timeout_seg} onChange={e => setForm({ ...form, timeout_seg: +e.target.value })} style={{ marginTop: '0.2rem' }} />
            </label>
            <label style={{ fontSize: '0.85rem' }}>
              Visibilidad
              <select className="input" value={form.visibility} onChange={e => setForm({ ...form, visibility: e.target.value })} style={{ marginTop: '0.2rem' }}>
                <option value="public">public</option>
                <option value="hidden">hidden</option>
              </select>
            </label>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button className="btn" disabled={!isFormValid || saving} onClick={save}>{saving ? 'Guardando...' : editingId ? 'Guardar cambios' : 'Agregar caso'}</button>
            {editingId && <button className="btn btn-secondary" onClick={cancelEdit}>Cancelar</button>}
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Panel de checks estáticos
// ---------------------------------------------------------------------------

function ChecksPanel({ consignaId, checks, onRefresh }: {
  consignaId: number
  checks: CheckEstaticoOut[]
  onRefresh: () => void
}) {
  const [form, setForm] = useState<CheckFormData>(emptyCheck())
  const [editingId, setEditingId] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)

  function startEdit(c: CheckEstaticoOut) {
    setEditingId(c.id)
    setForm({ descripcion: c.descripcion, pattern: c.pattern, check_type: c.check_type, min_count: c.min_count })
  }

  function cancelEdit() {
    setEditingId(null)
    setForm(emptyCheck())
  }

  async function save() {
    setSaving(true)
    try {
      const url = editingId
        ? `${API}/admin/checks/${editingId}`
        : `${API}/admin/consignas/${consignaId}/checks`
      const method = editingId ? 'PUT' : 'POST'
      const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form) })
      if (!res.ok) throw new Error(await res.text())
      setForm(emptyCheck())
      setEditingId(null)
      onRefresh()
    } finally {
      setSaving(false)
    }
  }

  async function remove(id: number) {
    if (!confirm('¿Eliminar este check estático?')) return
    await fetch(`${API}/admin/checks/${id}`, { method: 'DELETE' })
    onRefresh()
  }

  const isFormValid = form.descripcion.trim() && form.pattern.trim()

  return (
    <div>
      <h3 style={{ marginBottom: '0.75rem' }}>Checks estáticos del código fuente</h3>
      <p style={{ color: '#718096', fontSize: '0.85rem', marginBottom: '0.75rem' }}>
        Se aplican con regex sobre el código fuente C del alumno antes de ejecutar.
      </p>

      {checks.length === 0 && <p style={{ color: '#718096', fontSize: '0.9rem' }}>No hay checks estáticos.</p>}

      {checks.map(c => (
        <div key={c.id} style={{ border: '1px solid #e2e8f0', borderRadius: '6px', padding: '0.75rem', marginBottom: '0.5rem', background: '#f7fafc' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <strong>{c.descripcion}</strong>
              <span style={{ marginLeft: '0.5rem', fontSize: '0.8rem', color: '#718096' }}>[{c.check_type}{c.check_type === 'count_gte' ? ` ≥${c.min_count}` : ''}]</span>
            </div>
            <div style={{ display: 'flex', gap: '0.4rem' }}>
              <button className="btn btn-secondary" style={{ padding: '0.2rem 0.6rem', fontSize: '0.8rem' }} onClick={() => startEdit(c)}>Editar</button>
              <button className="btn" style={{ padding: '0.2rem 0.6rem', fontSize: '0.8rem', background: '#fc8181', color: '#fff' }} onClick={() => remove(c.id)}>Eliminar</button>
            </div>
          </div>
          <code style={{ display: 'block', marginTop: '0.3rem', fontSize: '0.8rem', color: '#553c9a', background: '#faf5ff', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>{c.pattern}</code>
        </div>
      ))}

      <div style={{ border: '1px dashed #cbd5e0', borderRadius: '6px', padding: '0.75rem', marginTop: '1rem' }}>
        <strong style={{ fontSize: '0.9rem' }}>{editingId ? 'Editar check' : 'Agregar check estático'}</strong>
        <div style={{ display: 'grid', gap: '0.5rem', marginTop: '0.5rem' }}>
          <input className="input" placeholder="Descripción (ej: 'Usa malloc')" value={form.descripcion} onChange={e => setForm({ ...form, descripcion: e.target.value })} />
          <input className="input" placeholder="Patrón regex (ej: malloc\s*\()" style={{ fontFamily: 'monospace' }} value={form.pattern} onChange={e => setForm({ ...form, pattern: e.target.value })} />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
            <select className="input" value={form.check_type} onChange={e => setForm({ ...form, check_type: e.target.value })}>
              <option value="exists">exists — aparece al menos una vez</option>
              <option value="count_gte">count_gte — aparece N veces o más</option>
            </select>
            {form.check_type === 'count_gte' && (
              <label style={{ fontSize: '0.85rem' }}>
                Mínimo de ocurrencias
                <input className="input" type="number" min={1} value={form.min_count} onChange={e => setForm({ ...form, min_count: +e.target.value })} style={{ marginTop: '0.2rem' }} />
              </label>
            )}
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button className="btn" disabled={!isFormValid || saving} onClick={save}>{saving ? 'Guardando...' : editingId ? 'Guardar cambios' : 'Agregar check'}</button>
            {editingId && <button className="btn btn-secondary" onClick={cancelEdit}>Cancelar</button>}
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Vista de detalle de una consigna
// ---------------------------------------------------------------------------

function ConsignaDetail({ consignaId, onBack }: { consignaId: number; onBack: () => void }) {
  const [consigna, setConsigna] = useState<ConsignaDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [editingMeta, setEditingMeta] = useState(false)
  const [metaForm, setMetaForm] = useState<ConsignaFormData>(emptyConsigna())

  async function load() {
    setLoading(true)
    const res = await fetch(`${API}/consignas/${consignaId}`)
    const data: ConsignaDetail = await res.json()
    setConsigna(data)
    setMetaForm({ nombre: data.nombre, descripcion: data.descripcion, is_active: data.is_active, requires_tda: data.requires_tda, requires_void_pointer: data.requires_void_pointer, requires_modularization: data.requires_modularization })
    setLoading(false)
  }

  useEffect(() => { load() }, [consignaId])

  async function saveMeta() {
    const res = await fetch(`${API}/admin/consignas/${consignaId}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(metaForm) })
    if (res.ok) { setEditingMeta(false); load() }
  }

  if (loading || !consigna) return <div className="card"><p>Cargando...</p></div>

  return (
    <>
      <button className="btn btn-secondary" style={{ marginBottom: '1rem' }} onClick={onBack}>← Volver a consignas</button>

      <div className="card">
        {!editingMeta ? (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h2 style={{ marginBottom: '0.25rem' }}>{consigna.nombre}</h2>
                <p style={{ color: '#718096', fontSize: '0.9rem', margin: 0 }}>{consigna.descripcion}</p>
              </div>
              <button className="btn btn-secondary" onClick={() => setEditingMeta(true)}>Editar</button>
            </div>
            <div style={{ marginTop: '0.75rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {consigna.is_active && <span className="status-badge status-ok">Activa</span>}
              {consigna.requires_tda && <span className="status-badge status-warning">Requiere TDA</span>}
              {consigna.requires_void_pointer && <span className="status-badge status-warning">Requiere void*</span>}
              {consigna.requires_modularization && <span className="status-badge status-warning">Requiere modularización</span>}
            </div>
          </>
        ) : (
          <div style={{ display: 'grid', gap: '0.5rem' }}>
            <h3 style={{ marginBottom: '0.25rem' }}>Editar consigna</h3>
            <input className="input" placeholder="Nombre" value={metaForm.nombre} onChange={e => setMetaForm({ ...metaForm, nombre: e.target.value })} />
            <textarea className="input" placeholder="Descripción" rows={3} value={metaForm.descripcion} onChange={e => setMetaForm({ ...metaForm, descripcion: e.target.value })} />
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
              {(['is_active', 'requires_tda', 'requires_void_pointer', 'requires_modularization'] as const).map(k => (
                <label key={k} style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.9rem', cursor: 'pointer' }}>
                  <input type="checkbox" checked={metaForm[k]} onChange={e => setMetaForm({ ...metaForm, [k]: e.target.checked })} />
                  {k.replace(/_/g, ' ')}
                </label>
              ))}
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button className="btn" onClick={saveMeta}>Guardar</button>
              <button className="btn btn-secondary" onClick={() => setEditingMeta(false)}>Cancelar</button>
            </div>
          </div>
        )}
      </div>

      <div className="card">
        <CasosPanel consignaId={consignaId} casos={consigna.casos_prueba} onRefresh={load} />
      </div>

      <div className="card">
        <ChecksPanel consignaId={consignaId} checks={consigna.checks_estaticos} onRefresh={load} />
      </div>
    </>
  )
}

// ---------------------------------------------------------------------------
// Lista de consignas
// ---------------------------------------------------------------------------

function ConsignaList({ onSelect }: { onSelect: (id: number) => void }) {
  const [consignas, setConsignas] = useState<{ id: number; nombre: string; descripcion: string; is_active: boolean }[]>([])
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState<ConsignaFormData>(emptyConsigna())
  const [saving, setSaving] = useState(false)

  async function load() {
    const res = await fetch(`${API}/consignas`)
    setConsignas(await res.json())
  }

  useEffect(() => { load() }, [])

  async function crear() {
    setSaving(true)
    try {
      const res = await fetch(`${API}/admin/consignas`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form) })
      if (!res.ok) throw new Error(await res.text())
      const nueva = await res.json()
      setCreating(false)
      setForm(emptyConsigna())
      await load()
      onSelect(nueva.id)
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ margin: 0 }}>Consignas</h2>
        <button className="btn" onClick={() => setCreating(true)}>+ Nueva consigna</button>
      </div>

      {creating && (
        <div className="card" style={{ marginBottom: '1rem' }}>
          <h3>Nueva consigna</h3>
          <div style={{ display: 'grid', gap: '0.5rem', marginTop: '0.5rem' }}>
            <input className="input" placeholder="Nombre (ej: 'TP1 - Pilas y Colas')" value={form.nombre} onChange={e => setForm({ ...form, nombre: e.target.value })} />
            <textarea className="input" placeholder="Descripción de la consigna" rows={3} value={form.descripcion} onChange={e => setForm({ ...form, descripcion: e.target.value })} />
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button className="btn" disabled={!form.nombre.trim() || saving} onClick={crear}>{saving ? 'Creando...' : 'Crear consigna'}</button>
              <button className="btn btn-secondary" onClick={() => { setCreating(false); setForm(emptyConsigna()) }}>Cancelar</button>
            </div>
          </div>
        </div>
      )}

      {consignas.length === 0 && !creating && (
        <div className="card">
          <p style={{ color: '#718096', textAlign: 'center' }}>No hay consignas todavía. Creá la primera.</p>
        </div>
      )}

      {consignas.map(c => (
        <div key={c.id} className="card" style={{ cursor: 'pointer', borderLeft: `4px solid ${c.is_active ? '#68d391' : '#cbd5e0'}` }} onClick={() => onSelect(c.id)}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <strong>{c.nombre}</strong>
              <p style={{ color: '#718096', fontSize: '0.85rem', margin: '0.2rem 0 0' }}>{c.descripcion}</p>
            </div>
            <span style={{ color: '#a0aec0', fontSize: '0.85rem' }}>Ver →</span>
          </div>
        </div>
      ))}
    </>
  )
}

// ---------------------------------------------------------------------------
// AdminView — raíz del módulo admin
// ---------------------------------------------------------------------------

export default function AdminView() {
  const [selectedId, setSelectedId] = useState<number | null>(null)

  return (
    <div className="container">
      {selectedId === null
        ? <ConsignaList onSelect={setSelectedId} />
        : <ConsignaDetail consignaId={selectedId} onBack={() => setSelectedId(null)} />
      }
    </div>
  )
}
