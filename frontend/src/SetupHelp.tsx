import {useState} from 'react'
import type {Config} from './types'
import {Modal} from './Modal'
import {ScoringHelp} from './ScoringHelp'
import styles from './SetupHelp.module.css'

export function SetupHelp({config, onClose, onRefresh, onExample, onUpload, onChecklist}: {
  config?: Config; onClose: () => void; onRefresh: () => Promise<void>;
  onExample: () => void; onUpload: () => void; onChecklist: () => void
}) {
  const [checking, setChecking] = useState(false), [error, setError] = useState('')
  const remaining = config ? Math.max(0, config.ledger.lifetime_limit_usd - config.ledger.lifetime_committed_usd) : 0
  async function check() {
    setChecking(true); setError('')
    try {await onRefresh()} catch {setError('Не удалось связаться с сервером. Убедитесь, что окно запуска открыто, и повторите попытку.')}
    finally {setChecking(false)}
  }
  return <Modal title="Настройка и помощь" onClose={onClose} wide>
    <div className={styles.help}>
      <p>Начните с готового учебного разбора — он открывается бесплатно, без API-ключа. Затем проверьте свои диалоги.</p>
      <div className={styles.columns}><div>
      <section className={styles.readiness} aria-label="Готовность к проверке">
        <div className={styles.heading}><h3>Для проверки своих данных</h3><button disabled={checking} onClick={check}>{checking ? 'Проверяем…' : 'Обновить статус'}</button></div>
        <ul>
          <li><span>Сервер приложения</span><b data-ok={!!config && !error}>{error ? 'Недоступен' : config ? 'Доступен' : 'Не проверен'}</b></li>
          <li><span>API-ключ</span><b data-ok={!!config?.api_key_configured}>{!config ? 'Не проверен' : config.api_key_configured ? 'Указан' : 'Не указан'}</b></li>
          <li><span>Остаток лимита расходов</span><b data-ok={!!config && remaining > 0}>{config ? remaining.toLocaleString('ru-RU', {style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 4}) : 'Не проверен'}</b></li>
        </ul>
        <p>Проверка статуса бесплатна. Доступ к модели и баланс счёта проверяются при запуске оценки.</p>
        {error && <p role="alert" className={styles.problem}>{error}</p>}
      </section>
      <details open={config && (!config.api_key_configured || remaining <= 0) || undefined}>
        <summary>Первый запуск и настройка</summary>
        <p>Клонируйте проект с GitHub и выполните команды из <code>README.md</code>. Для запуска из папки проекта используйте <code>./scripts/start-local.ps1</code> в Windows или <code>sh scripts/start-local.sh</code> в Linux.</p>
        <p>Для новых проверок укажите <code>OPENAI_API_KEY</code> в локальном файле <code>.env</code>. После добавления или замены ключа перезапустите сервер. Учебный разбор доступен и без ключа.</p>
        <p>Оставьте окно запуска открытым во время работы. Для остановки нажмите Ctrl+C.</p>
        <details><summary>Если достигнут лимит расходов</summary>
          <p>Общий лимит задаётся в <code>CQA_MAX_SPEND_USD</code> в файле <code>.env</code>. Увеличивайте его только до суммы, которую готовы потратить, затем перезапустите приложение. Этот лимит не пополняет баланс счёта у поставщика модели.</p>
        </details>
      </details>
      </div>
      <section className={styles.walkthrough} aria-label="Инструкция для жюри">
        <h3>Как попробовать</h3>
        <ol>
          <li><b>Нажмите «Открыть пример».</b> Сразу появится готовый разбор с оценкой, диалогом и справочной статьёй. Ключ и оплата не нужны.</li>
          <li><b>Разберитесь в оценке.</b> В примере набрано 70 из 80 возможных баллов: 70 ÷ 80 × 100 = 87,5. Проверка личности не требовалась, поэтому её 20 баллов исключены из расчёта.</li>
          <li><b>Проверьте обоснование.</b> Откройте «Обоснование и цитаты». Нажатие на цитату выделит её в диалоге. В примере оператор объясняет, как изменить адрес в профиле, но не отвечает на вопрос об уже оформленном заказе.</li>
          <li><b>Добавьте свои данные.</b> Нажмите «Загрузить данные» и вставьте текст или выберите файл. Свой чек-лист создайте в разделе «Критерии оценки». Справку добавьте рядом с диалогом: «Добавить свой документ» — текст или файл TXT/MD.</li>
          <li><b>Запустите новую проверку.</b> Нажмите «Начать проверку» над открытым диалогом, выберите чек-лист и проверьте лимит расходов. Для нескольких диалогов выделите их в списке и нажмите «Проверить выбранные».</li>
        </ol>
        <div className={styles.actions}><button onClick={onExample}>Открыть пример</button><button onClick={onUpload}>Загрузить данные</button><button onClick={onChecklist}>Создать чек-лист</button></div>
      </section>
      </div>
      <ScoringHelp/>
      <details><summary>Если результат требует уточнения</summary>
        <p><b>Предварительная оценка</b> означает, что часть выводов зависит от непроверенных сведений. Откройте «Что нужно уточнить» у соответствующего критерия. Если вы не согласны с выводом, выберите «Запросить пересмотр».</p>
        <p>При ошибке прочитайте причину и проверьте настройки перед повторным запуском. Новая проверка может потребовать расходов. Просмотр сохранённых результатов бесплатен.</p>
      </details>
      <details><summary>Язык и исходные данные</summary>
        <p>Интерфейс и обоснования новых оценок — на русском. Сообщения, цитаты, загруженные чек-листы и ранее сохранённые обоснования остаются на языке оригинала.</p>
      </details>
    </div>
  </Modal>
}
