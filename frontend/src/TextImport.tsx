import {useState} from 'react'
import {parseTranscript, type TranscriptMessage} from './transcriptImport'
import styles from './App.module.css'

export function TextImport({busy, onImport, onClose}: {busy: boolean; onImport: (content: string) => Promise<void>; onClose: () => void}) {
  const [text, setText] = useState(''), [language, setLanguage] = useState('RU')
  const [channel, setChannel] = useState('agent chat'), [preparing, setPreparing] = useState(false), [error, setError] = useState('')
  let messages: TranscriptMessage[] = [], problem = ''
  if (text.trim()) {
    try {messages = parseTranscript(text)} catch (e) {problem = (e as Error).message}
  }
  async function submit() {
    if (!messages.length || problem) return
    setPreparing(true); setError('')
    try {
      const body = {channel, language, messages, references: []}
      const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(body)))
      const id = `text-${Array.from(new Uint8Array(hash)).map(byte => byte.toString(16).padStart(2, '0')).join('').slice(0, 24)}`
      await onImport(JSON.stringify({...body, id}))
    } catch (e) {setError((e as Error).message)} finally {setPreparing(false)}
  }
  return <>
    <p>Вставьте переписку. Начинайте каждую реплику с «Клиент:» или «Оператор:». Для бота и служебных сообщений используйте «Бот:» и «Система:».</p>
    <div className={styles.textImportOptions}>
      <label>Тип диалога<select value={channel} onChange={e => setChannel(e.target.value)}><option value="agent chat">Чат</option><option value="voice call">Расшифровка звонка</option></select></label>
      <label>Язык диалога<select value={language} onChange={e => setLanguage(e.target.value)}><option value="RU">Русский</option><option value="KZ">Казахский</option><option value="EN">Английский</option></select></label>
    </div>
    <label>Текст диалога<textarea rows={7} value={text} onChange={e => {setText(e.target.value); setError('')}} placeholder={'Клиент: Где посмотреть статус заявки?\nОператор: Здравствуйте! Откройте раздел «Мои заявки».\nКлиент: Спасибо, нашёл.'}/></label>
    <p className={styles.muted}>Время необязательно: [00:15] Клиент: … Если его нет, мы не придумываем отметки времени. Для проверки фактов справочные материалы можно добавить после загрузки.</p>
    {(problem || error) && <p role="alert" className={styles.warning}>{problem || error}</p>}
    {messages.length > 0 && !problem && <details className={styles.textPreview}><summary>Проверить перед загрузкой · сообщений: {messages.length}</summary>
      {messages.map(m => <p key={m.id}><b>{m.speaker === 'client' ? 'Клиент' : m.speaker === 'operator' ? 'Оператор' : m.speaker === 'bot' ? 'Бот' : 'Система'}{m.timestamp ? ` · ${m.timestamp}` : ''}</b><br/>{m.text}</p>)}
    </details>}
    <p className={styles.muted}>Загрузка бесплатна. Проверка запускается отдельно.</p>
    <div className={styles.dialogFooter}><button onClick={onClose}>Отмена</button><button className={styles.primary} disabled={busy || preparing || !!problem || !messages.length} onClick={submit}>{busy || preparing ? 'Загрузка…' : 'Добавить диалог'}</button></div>
  </>
}
