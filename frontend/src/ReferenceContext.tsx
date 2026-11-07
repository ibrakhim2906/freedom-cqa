import {useEffect, useState} from 'react'
import type {ConversationDetail, EvidenceContext, ReferenceMode, ReferencePack} from './types'
import {api} from './api'
import {referenceDate, safeLink} from './format'
import styles from './App.module.css'

type Selection = {pack_id: string; scope: string; mode: ReferenceMode; occurred_on: string|null;
  as_of: string|null; rationale: string}

export function ReferenceContext({source, onApplied, onError}: {
  source: ConversationDetail; onApplied: (id: string) => Promise<void>; onError: (s: string) => void
}) {
  const [packs, setPacks] = useState<ReferencePack[]>([]), [context, setContext] = useState<EvidenceContext>()
  const [selected, setSelected] = useState(''), [mode, setMode] = useState<ReferenceMode>('conversation_date')
  const [occurredOn, setOccurredOn] = useState(source.content.occurred_on || ''), [asOf, setAsOf] = useState('')
  const [rationale, setRationale] = useState(''), [scopeConfirmed, setScopeConfirmed] = useState(false)
  const [pending, setPending] = useState(false), [error, setError] = useState('')
  const [preview, setPreview] = useState<{key: string; context: EvidenceContext}>()
  useEffect(() => {
    let cancelled = false
    Promise.all([api<ReferencePack[]>('/reference-packs'), api<EvidenceContext>(`/conversations/${source.id}/evidence-context`)])
      .then(([available, saved]) => {if (!cancelled) {setPacks(available); setContext(saved); setOccurredOn(saved.temporal.occurred_on || '')}})
      .catch(e => {if (!cancelled) {setError(e.message); onError(e.message)}})
    return () => {cancelled = true}
  }, [source.id, onError])
  const pack = packs.find(p => p.id === selected)
  const snapshotDates = [...new Set(pack?.references.map(r => r.snapshot_on).filter((on): on is string => !!on) || [])].sort()
  const selection: Selection = {pack_id: selected, scope: pack?.scope || '', mode,
    occurred_on: mode === 'conversation_date' ? occurredOn || null : null,
    as_of: mode === 'snapshot_review' ? asOf || null : null, rationale: rationale.trim()}
  const key = JSON.stringify(selection)
  const currentPreview = preview?.key === key ? preview.context : undefined
  const previewRefs = currentPreview?.references.filter(r => pack?.references.some(ref => ref.id === r.reference_id)) || []
  const validSelection = !!(pack && scopeConfirmed && selection.rationale &&
    (mode === 'conversation_date' ? occurredOn : asOf) && !context?.temporal.has_conflict)
  const usable = previewRefs.filter(r => r.usable).length
  async function previewSelection() {
    setPending(true); setError(''); setPreview(undefined)
    try {setPreview({key, context: await api<EvidenceContext>(`/conversations/${source.id}/references/preview`, selection)})}
    catch (e) {setError((e as Error).message); onError((e as Error).message)} finally {setPending(false)}
  }
  return <details className={styles.context}>
    <summary>Reference context · {source.reference_count} attached</summary>
    <p>Actual conversation date: <b>{context?.temporal.occurred_on || source.content.occurred_on || 'unknown'}</b>
      {context && <> · Date source: {context.temporal.origin.replaceAll('_', ' ')}</>}</p>
    <p>Recorded product scope: {source.content.knowledge_scope || 'unknown'}</p>
    {context?.temporal.has_conflict && <p role="alert" className={styles.error}>Source dates conflict: {context.temporal.conflict_reason}. Resolve the source metadata before selecting references.</p>}
    {context?.assessment.conditional && <div className={styles.warning}><b>Conditional snapshot review</b>
      <p>Product assumption: {context.assessment.scope} · Assessment as of {context.assessment.as_of}. The original conversation date and scope remain unchanged.</p>
      <p>{context.assessment.rationale}</p></div>}
    {!!context?.references.length && <details><summary>Current source applicability · {context.references.filter(r => r.usable).length}/{context.references.length} usable</summary>
      {context.references.map(r => <p key={r.reference_id}>{r.reference_id}: {r.usable ? 'Usable' : `Unavailable — ${r.rejection_reasons.join(', ').replaceAll('_', ' ')}`}</p>)}</details>}
    <p>Select an assessment basis and preview which official sources can support it. Applying creates a new revision; saved assessments keep their original inputs.</p>
    {error && <p role="alert" className={styles.error}>{error}</p>}
    <label>Reference pack<select aria-label="Reference pack" value={selected} onChange={e => {
      const next = packs.find(p => p.id === e.target.value)
      setSelected(e.target.value); setScopeConfirmed(false); setError(''); setPreview(undefined)
      const dates = [...new Set(next?.references.map(r => r.snapshot_on).filter((on): on is string => !!on) || [])]
      setAsOf(dates.length === 1 ? dates[0] : '')
    }}><option value="">Choose reference pack</option>{packs.map(p => <option key={p.id} value={p.id}>{p.title || p.id} · {p.scope}</option>)}</select></label>
    <label>Assessment basis<select aria-label="Reference assessment basis" value={mode} onChange={e => {setMode(e.target.value as ReferenceMode); setScopeConfirmed(false); setError(''); setPreview(undefined)}}>
      <option value="conversation_date">Assess against the actual conversation date</option>
      <option value="snapshot_review">Conditional review against a source snapshot</option>
    </select></label>
    {mode === 'conversation_date' ? <label>Known conversation date<input aria-label="Known conversation date" type="date" value={occurredOn}
      disabled={!!context?.temporal.occurred_on} onChange={e => {setOccurredOn(e.target.value); setError('')}}/></label> : <>
      <p className={styles.warning}>This assumes the selected product and snapshot for review. It does not establish the original conversation's entity or historical policy.</p>
      <label>Snapshot assessment date<input aria-label="Snapshot assessment date" type="date" value={asOf} onChange={e => {setAsOf(e.target.value); setError('')}}/></label>
      {snapshotDates.length > 0 && <p>Available source snapshots: {snapshotDates.join(', ')}. These are retrieval snapshots, not legal effective dates.</p>}
    </>}
    {pack && <label><input aria-label="Confirm reference scope" type="checkbox" checked={scopeConfirmed} onChange={e => setScopeConfirmed(e.target.checked)}/>
      {mode === 'conversation_date' ? `The conversation concerns ${pack.scope}.` : `Use ${pack.scope} as the explicit product assumption for this conditional review.`}</label>}
    <label>{mode === 'conversation_date' ? 'Evidence for the product scope and conversation date' : 'Reason for the product and snapshot assumption'}
      <textarea aria-label="Reference context rationale" rows={3} value={rationale} onChange={e => {setRationale(e.target.value); setError('')}}/></label>
    <div className={styles.row}>
      <button disabled={!validSelection || pending} onClick={previewSelection}>Preview applicability (no API evaluation)</button>
      <button disabled={!validSelection || pending || !currentPreview || !usable} onClick={async () => {
        setPending(true); setError('')
        try {const value = await api<ConversationDetail>(`/conversations/${source.id}/references`, selection); await onApplied(value.id)}
        catch (e) {setError((e as Error).message); onError((e as Error).message)} finally {setPending(false)}
      }}>Apply as new revision</button>
    </div>
    {currentPreview && <div role="status"><b>{usable}/{previewRefs.length} selected-pack sources usable</b>
      {currentPreview.assessment.conditional && <p className={styles.warning}>Any resulting assessment is conditional on {currentPreview.assessment.scope} as of {currentPreview.assessment.as_of}.</p>}
      {previewRefs.map(r => <p key={r.reference_id}>{r.reference_id}: {r.usable ? 'Usable' : `Unavailable — ${r.rejection_reasons.join(', ').replaceAll('_', ' ')}`}</p>)}
      {!usable && <p>These sources cannot support this context. Correct the context or choose applicable source material; do not change the conversation date to fit a source.</p>}
    </div>}
    {pack && <details><summary>Selected source details and limitations</summary>{pack.usage_notes?.map((n, i) => <p key={i}>{n}</p>)}
      {pack.references.map(r => <p key={r.id}>{r.id} · {referenceDate(r)} · {safeLink(r.source_url) && <a href={safeLink(r.source_url)} target="_blank" rel="noreferrer">Official source</a>}</p>)}
    </details>}
  </details>
}
