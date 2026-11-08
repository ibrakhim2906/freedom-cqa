import type {Checklist, Criterion} from './types'
import styles from './App.module.css'

export function newCriterion(): Criterion {
  return {id: `criterion-${Date.now()}`, title: 'New criterion', instruction: '', kind: 'binary', weight: 10,
    na_condition: null, channel_guidance: {}, levels: [{value: 'yes', fraction: 1, description: 'The defined condition is met.'}, {value: 'no', fraction: 0, description: 'The defined condition is not met.'}]}
}
export function ChecklistEditor({value, onChange, onSave, busy}: {value: Checklist; onChange: (c: Checklist) => void; onSave: () => void; busy: boolean}) {
  const change = (i: number, patch: Partial<Criterion>) => onChange({...value, criteria: value.criteria.map((c, n) => n === i ? {...c, ...patch} : c)})
  return <div className={styles.editor}>
    <div className={styles.editorActions}><div><b>{value.criteria.length} configured criteria</b><span>Save a new version to use these changes in an evaluation.</span></div><button onClick={() => onChange({...value, criteria: [...value.criteria, newCriterion()]})}>Add criterion</button><button className={styles.primary} disabled={busy} onClick={onSave}>Save checklist version</button></div>
    <div className={styles.row}><label>Checklist ID<input value={value.id} onChange={e => onChange({...value, id: e.target.value})}/></label>
      <label>Version<input value={value.version} onChange={e => onChange({...value, version: e.target.value})}/></label>
      <label>Title<input value={value.title} onChange={e => onChange({...value, title: e.target.value})}/></label></div>
    <label>Overall instructions (one per line)<textarea value={value.instructions.join('\n')} onChange={e => onChange({...value, instructions: e.target.value.split('\n').filter(Boolean)})}/></label>
    {value.criteria.map((c, i) => <fieldset key={i}><legend>Criterion {i + 1}</legend>
      <div className={styles.row}><label>ID<input value={c.id} onChange={e => change(i, {id: e.target.value})}/></label><label>Title<input value={c.title} onChange={e => change(i, {title: e.target.value})}/></label>
        <label>Kind<select value={c.kind} onChange={e => change(i, {kind: e.target.value as Criterion['kind'], weight: e.target.value === 'flag' ? 0 : c.weight})}>{['binary','scale','flag'].map(k => <option key={k}>{k}</option>)}</select></label>
        <label>Weight<input type="number" min="0" value={c.weight} onChange={e => change(i, {weight: Number(e.target.value)})}/></label></div>
      <label>Evaluation instruction<textarea aria-label={`Criterion ${i + 1} instruction`} value={c.instruction} onChange={e => change(i, {instruction: e.target.value})}/></label>
      <label>N/A condition (blank forbids N/A)<input value={c.na_condition || ''} onChange={e => change(i, {na_condition: e.target.value || null})}/></label>
      <label>Call-specific guidance<textarea value={c.channel_guidance['voice call'] || ''} onChange={e => change(i, {channel_guidance: {...c.channel_guidance, 'voice call': e.target.value}})}/></label>
      <p>Allowed answers and score fractions (0–1)</p>{c.levels.map((l, n) => <div key={n} className={styles.row}>
        <input aria-label={`Criterion ${i + 1} level ${n + 1} value`} value={l.value} onChange={e => change(i, {levels: c.levels.map((x, k) => k === n ? {...x, value: e.target.value} : x)})}/>
        <input aria-label={`Criterion ${i + 1} level ${n + 1} fraction`} type="number" step="0.05" min="0" max="1" value={l.fraction} onChange={e => change(i, {levels: c.levels.map((x, k) => k === n ? {...x, fraction: Number(e.target.value)} : x)})}/>
        <input aria-label={`Criterion ${i + 1} level ${n + 1} description`} value={l.description} onChange={e => change(i, {levels: c.levels.map((x, k) => k === n ? {...x, description: e.target.value} : x)})}/>
        <button onClick={() => change(i, {levels: c.levels.filter((_, k) => k !== n)})}>Remove level</button></div>)}
      <div className={styles.row}><button onClick={() => change(i, {levels: [...c.levels, {value: `level-${c.levels.length + 1}`, fraction: 0.5, description: ''}]})}>Add level</button>
        <button onClick={() => onChange({...value, criteria: value.criteria.filter((_, n) => n !== i)})}>Remove criterion</button></div>
    </fieldset>)}
  </div>
}
