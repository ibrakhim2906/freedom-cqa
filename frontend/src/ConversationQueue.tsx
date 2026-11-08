import {useEffect, useId, useRef, useState} from 'react'
import type {ConversationRow} from './types'
import {Icon} from './Icon'
import {date} from './format'
import {scoreNumber} from './scorePresentation'
import {groupConversationRevisions} from './conversationRevisions'
import styles from './ConversationQueue.module.css'

function conversationTitle(c: ConversationRow) {
  return c.display_title?.trim() || `${c.channel === 'voice call' ? 'Звонок' : 'Чат'}${c.language.trim() ? ` · ${c.language.toUpperCase()}` : ''}`
}

export function ConversationQueue({conversations, selected, current, onSelect, onChoose, onOpenAssessment}: {
  conversations: ConversationRow[]; selected: string[]; current: string;
  onSelect: (ids: string[]) => void; onChoose: (id: string) => void;
  onOpenAssessment: (jobId: string, revisionId: string) => void;
}) {
  const [query, setQuery] = useState(''), [language, setLanguage] = useState(''), [channel, setChannel] = useState('')
  const [assessmentFilter, setAssessmentFilter] = useState(''), [expanded, setExpanded] = useState<string[]>([])
  const [filtersOpen, setFiltersOpen] = useState(false)
  const filtersId = useId(), historyId = useId()
  const filterCount = [language, channel, assessmentFilter].filter(Boolean).length
  const resetFilters = () => {setLanguage(''); setChannel(''); setAssessmentFilter('')}
  const all = useRef<HTMLInputElement>(null)
  const groups = groupConversationRevisions(conversations)
  const languages = [...new Set(groups.map(group => group.latest.language))].sort()
  const matching = groups.filter(({latest: c}) => {
    const assessment = c.latest_assessment
    return [c.external_id, conversationTitle(c)].some(text => text.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()))
      && (!language || c.language === language) && (!channel || c.channel === channel)
      && (!assessmentFilter || (assessmentFilter === 'unassessed' && assessment === null)
        || (assessmentFilter === 'review' && !!assessment && (assessment.review_recommended_count > 0 || (assessment.open_appeals || 0) > 0))
        || (assessmentFilter === 'completed' && assessment?.status === 'completed')
        || (assessmentFilter === 'active' && !!assessment && ['queued', 'running'].includes(assessment.status))
        || (assessmentFilter === 'failed' && !!assessment && ['failed', 'interrupted', 'cancelled'].includes(assessment.status)))
  })
  // Reveal a selected historical result once; collapsing history never changes the open transcript.
  const currentGroup = groups.find(group => group.revisions.some(revision => revision.id === current))
  const currentGroupId = currentGroup?.externalId, currentLatestId = currentGroup?.latest.id
  useEffect(() => {
    if (currentGroupId && currentLatestId !== current) setExpanded(old => old.includes(currentGroupId) ? old : [...old, currentGroupId])
  }, [current, currentGroupId, currentLatestId])
  const isExpanded = (group: typeof groups[number]) => expanded.includes(group.externalId)
  const visible = matching.flatMap(group => isExpanded(group) ? group.revisions : [group.latest])
  const picked = new Set(selected), selectedVisible = visible.filter(c => picked.has(c.id)).length
  useEffect(() => {if (all.current) all.current.indeterminate = selectedVisible > 0 && selectedVisible < visible.length}, [selectedVisible, visible.length])
  const toggleVisible = (checked: boolean) => {
    const visibleIds = new Set(visible.map(c => c.id))
    onSelect(checked ? [...new Set([...selected, ...visibleIds])] : selected.filter(id => !visibleIds.has(id)))
  }
  function revisionRow(c: ConversationRow, latest: boolean, group: typeof groups[number]) {
    const showDetails = isExpanded(group)
    const assessment = c.latest_assessment
    const savedLabel = assessment === undefined ? 'Статус недоступен' : assessment === null ? 'Без оценки'
      : assessment.status === 'completed' ? assessment.total === null ? 'Проверено · без балла'
        : `${scoreNumber(assessment.total)}/100`
      : assessment.status === 'queued' ? 'В очереди' : assessment.status === 'running' ? 'Идёт проверка…'
      : assessment.status === 'failed' ? 'Ошибка проверки' : assessment.status === 'interrupted' ? 'Проверка прервана'
      : assessment.status === 'cancelled' ? 'Проверка отменена' : assessment.status
    return <div key={c.id} data-testid={`queue-revision-${c.id}`} className={`${styles.conversationRow} ${!latest ? styles.olderRevision : ''} ${current === c.id ? styles.selected : ''}`}>
      <input aria-label={`Выбрать ${c.external_id}${latest ? '' : `, версия ${c.content_hash.slice(0, 7)}`}`} type="checkbox" checked={picked.has(c.id)} onChange={e => onSelect(e.target.checked ? [...new Set([...selected, c.id])] : selected.filter(id => id !== c.id))}/>
      <div className={styles.conversationBody}>
        <div className={styles.rowMain}>
        <button className={styles.chooseConversation} title={conversationTitle(c)} aria-current={current === c.id ? 'true' : undefined} onClick={() => onChoose(c.id)}><b>{conversationTitle(c)}</b>
          <span className={styles.conversationMeta}><Icon name={c.channel === 'voice call' ? 'call' : 'chat'} size={13}/>{c.channel === 'voice call' ? 'Звонок' : 'Чат'} · {c.language} · Сообщений: {c.message_count}</span>
        </button>
        {assessment ? <button className={styles.queueAssessment} data-status={assessment.status} data-provisional={assessment.provisional || undefined}
          aria-label={`Открыть оценку ${c.external_id}, версия ${c.content_hash.slice(0, 7)}`} title={assessment.provisional ? 'Предварительная оценка: результат может измениться после пересмотра' : assessment.status === 'completed' ? 'Открыть сохранённый результат' : 'Посмотреть ход проверки'}
          onClick={() => onOpenAssessment(assessment.id, c.id)}><span>{savedLabel}</span>{assessment.is_demo && <small>Учебный разбор</small>}{assessment.status === 'completed' && assessment.provisional && <small>Нужен пересмотр</small>}<Icon name="arrow" size={13}/></button>
          : <span className={styles.unassessed}>{savedLabel}</span>}
        </div>
        <div className={styles.rowFooter}>
        {(!!assessment?.review_recommended_count || !!assessment?.open_appeals) && <div className={styles.reviewSummary}>
          {!!assessment.review_recommended_count && <span title={`Пунктов для пересмотра: ${assessment.review_recommended_count}`}>Требуют внимания: {assessment.review_recommended_count}</span>}
          {!!assessment.open_appeals && <span>Открытых запросов: {assessment.open_appeals}</span>}
        </div>}
        {latest && <button className={styles.revisionToggle} aria-expanded={showDetails} aria-controls={`${historyId}-${group.latest.id}-meta ${historyId}-${group.latest.id}`} aria-label={group.revisions.length > 1 ? `История версий ${group.externalId}` : `Сведения о ${group.externalId}`}
          onClick={() => setExpanded(old => showDetails ? old.filter(id => id !== group.externalId) : [...old, group.externalId])}>
          {group.revisions.length > 1 ? `Версии (${group.revisions.length})` : 'Подробнее'}<span aria-hidden="true">{showDetails ? '−' : '+'}</span></button>}
        </div>
        <div id={`${historyId}-${c.id}-meta`} hidden={!showDetails} className={styles.revisionMeta}><span>Идентификатор: {c.external_id}</span><span>{latest ? 'Текущая' : 'Предыдущая'} версия <code>{c.content_hash.slice(0, 7)}</code></span><span>Загружено: {date(c.created_at)}</span></div>
      </div>
    </div>
  }
  return <aside className={styles.sidebar} aria-label="Список диалогов">
    <div className={styles.queueHeading}><h2>Диалоги</h2><span className={styles.count}>{groups.length}</span></div>
    <div className={styles.search}><Icon name="search" size={16}/><input type="search" aria-label="Поиск диалогов" placeholder="Найти диалог" value={query} onChange={e => setQuery(e.target.value)}/></div>
    <div className={styles.filterBar}>
      <button className={styles.filterToggle} aria-expanded={filtersOpen} aria-controls={filtersId} onClick={() => setFiltersOpen(open => !open)}><Icon name="settings" size={14}/>Фильтры{filterCount > 0 && <span className={styles.filterCount}>{filterCount}</span>}<span aria-hidden="true">{filtersOpen ? '−' : '+'}</span></button>
      {filterCount > 0 && <button className={styles.quiet} onClick={resetFilters}>Сбросить фильтры</button>}
    </div>
    <div id={filtersId} hidden={!filtersOpen} className={styles.filters}>
      <label>Язык<select aria-label="Фильтр по языку" value={language} onChange={e => setLanguage(e.target.value)}><option value="">Все языки</option>{languages.map(l => <option key={l} value={l}>{l}</option>)}</select></label>
      <label>Тип диалога<select aria-label="Фильтр по типу диалога" value={channel} onChange={e => setChannel(e.target.value)}><option value="">Все типы</option><option value="agent chat">Чат</option><option value="voice call">Звонок</option></select></label>
      <label className={styles.assessmentFilter}>Статус<select aria-label="Фильтр по статусу" value={assessmentFilter} onChange={e => setAssessmentFilter(e.target.value)}><option value="">Все статусы</option><option value="review">Требуют внимания</option><option value="unassessed">Без оценки</option><option value="completed">Проверено</option><option value="active">В очереди или на проверке</option><option value="failed">Ошибка или остановка</option></select></label>
    </div>
    <div className={styles.queueSelection}><label><input ref={all} type="checkbox" disabled={!visible.length} checked={visible.length > 0 && selectedVisible === visible.length} onChange={e => toggleVisible(e.target.checked)}/> Выбрать показанные</label>
      {selected.length ? <button className={styles.quiet} onClick={() => onSelect([])} aria-label="Снять выделение диалогов">Снять выбор ({selected.length})</button> : <span aria-live="polite">Найдено: {matching.length}</span>}</div>
    {selected.length > selectedVisible && <p className={styles.queueHint}>Выбранных версий за пределами списка: {selected.length - selectedVisible}. Они скрыты фильтрами или находятся в свёрнутой истории.</p>}
    <div className={styles.queueItems}>{matching.map(group => <div key={group.externalId} className={styles.revisionGroup}>
      {revisionRow(group.latest, true, group)}
      <div id={`${historyId}-${group.latest.id}`} hidden={!isExpanded(group)}>{isExpanded(group) && group.revisions.slice(1).map(c => revisionRow(c, false, group))}</div>
    </div>)}</div>
    {!visible.length && <div className={styles.empty}><Icon name="search" size={23}/><p>{conversations.length ? 'По вашему запросу ничего не найдено.' : 'Диалогов пока нет. Загрузите файл с данными.'}</p>
      {conversations.length > 0 && <button onClick={() => {setQuery(''); resetFilters()}}>Сбросить поиск и фильтры</button>}</div>}
  </aside>
}
