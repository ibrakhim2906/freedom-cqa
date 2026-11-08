import {test, expect, type Page} from '@playwright/test'

// All API traffic is fulfilled in memory. This suite cannot submit an evaluation or write to the database.
test.use({baseURL: process.env.CQA_UI_BASE_URL || 'http://127.0.0.1:8010', actionTimeout: 15000})
const uncertainty = 'The applicable withdrawal fee has not been established.'
const recording = 'https://example.invalid/call.mp3'
const checklist = {id: 'checklist-doc', external_id: 'qa', version: '1', content_hash: 'checklist-hash', title: 'Synthetic QA',
  content: {id: 'qa', version: '1', title: 'Synthetic QA', instructions: [], criteria: [{id: 'advice', title: 'Advice',
    instruction: 'Grade the advice using the supplied evidence.', kind: 'scale', weight: 10, na_condition: null, channel_guidance: {},
    levels: [{value: '10', fraction: 1, description: 'Complete'}, {value: '5', fraction: 0.5, description: 'Partial'}, {value: '0', fraction: 0, description: 'Incorrect'}]}]}}
const messages = [{id: 'm1', timestamp: '00:00', speaker: 'client', text: 'What fee applies?'},
  {id: 'm2', timestamp: '00:01', speaker: 'operator', text: 'I will check the fee.'},
  {id: 'm3', timestamp: '00:02', speaker: 'operator', text: 'Please check the attached tariff before proceeding.'}]
const summary = {id: 'job-new', status: 'completed', total: 50, provisional: true, review_recommended_count: 1, open_appeals: 1}
const latest = {id: 'doc-new', external_id: 'call-1', display_title: 'What fee applies?', content_hash: 'newhash123', created_at: '2026-11-08T08:00:00Z', channel: 'voice call', language: 'EN', message_count: 3, reference_count: 0, latest_assessment: summary}
const older = {...latest, id: 'doc-old', content_hash: 'oldhash123', created_at: '2026-11-07T08:00:00Z', latest_assessment: {...summary, id: 'job-old', total: 100, provisional: false, review_recommended_count: 0, open_appeals: 0}}
const unassessed = {...latest, id: 'doc-chat', external_id: 'chat-2', display_title: 'Can I update my details?', channel: 'agent chat', content_hash: 'chathash123', latest_assessment: null}
const jobRow = {id: 'job-new', batch_id: 'batch', conversation_id: latest.id, checklist_id: checklist.id, status: 'completed',
  review_revision: 0, created_at: latest.created_at, started_at: null, finished_at: null, retry_of: null}
const judgment = {criterion_id: 'advice', status: 'scored', answer: '5', explanation: 'A provisional assessment of the supplied advice.',
  evidence: [{message_id: 'm2', quote: messages[1].text}], counterevidence: [], checked_message_ids: ['m1', 'm2', 'm3'], uncertainty}
const score = {total: 50, provisional: true, flags: {}, unresolved_criteria: [], review_recommended_criteria: ['advice'],
  score_bounds: {lower: 0, upper: 100}, contributions: [{criterion_id: 'advice', status: 'scored', points: 5}]}
const appeal = {id: 'appeal-1', job_id: jobRow.id, criterion_id: 'advice', author: 'Synthetic reviewer', reason: 'Review the grade while retaining missing policy facts.',
  message_ids: ['m3'], proposed: null, status: 'open', created_at: latest.created_at, resolution: null}
const evidenceContext = {temporal: {occurred_on: null, origin: 'unknown', has_conflict: false},
  assessment: {mode: 'conversation_date', conditional: false, scope: null, as_of: null}, references: []}

function detail(row: typeof latest | typeof unassessed) {
  return {...row, content: {id: row.external_id, channel: row.channel, language: row.language, messages, references: []},
    metadata: row.channel === 'voice call' ? {recording_url: recording} : {}}
}
function savedJob(old = false) {
  const row = old ? older : latest
  const effectiveScore = old ? {...score, total: 100, provisional: false, review_recommended_criteria: []} : score
  return {...jobRow, id: old ? 'job-old' : 'job-new', conversation_id: row.id, conversation: detail(row), checklist, appeals: old ? [] : [appeal],
    effective: {judgments: [judgment], score: effectiveScore, source: 'ai_original', accepted_revisions: 0},
    record: {evaluation: {judgments: [judgment], factual_claims: [], scope_notes: [], request_coverage: [], deductions: []}, score: effectiveScore,
      error: null, model: 'synthetic-ui-fixture', prompt_version: 'fixture', workflow_version: 'fixture', response_id: null,
      usage: null, attempt_count: 1, latency_seconds: 0}}
}

async function fixture(page: Page) {
  const writes: {path: string; body: Record<string, unknown>}[] = []
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.route('https://example.invalid/**', route => route.abort())
  await page.route('**/api/**', route => {
    const request = route.request(), url = new URL(request.url()), path = url.pathname
    const respond = (json: unknown, status = 200) => route.fulfill({status, json})
    if (request.method() !== 'GET') {
      writes.push({path, body: request.postDataJSON()})
      if (path === '/api/appeals/appeal-1/resolve') return respond({})
      if (path === '/api/conversations/import') return respond({created: 0, reused: 1, conversations: [latest]})
      return respond({detail: 'Unexpected mutation blocked by synthetic test'}, 403)
    }
    if (path === '/api/config') return respond({api_key_configured: false, model: 'fixture', strategy: 'assessor', default_checklist: {id: 'qa', version: '1'}, ledger: {lifetime_committed_usd: 0, lifetime_limit_usd: 0}})
    if (path === '/api/conversations') return respond([latest, unassessed, older])
    if (path === '/api/checklists') return respond([checklist])
    if (path === '/api/reference-packs') return respond([])
    if (path.endsWith('/evidence-context')) return respond(evidenceContext)
    if (path.endsWith('/reference-options')) return respond({references: []})
    if (path.endsWith('/comparison-candidates')) return respond([])
    if (path === '/api/jobs') return respond(url.searchParams.get('conversation_id') === older.id ? [{...jobRow, id: 'job-old', conversation_id: older.id}] : [jobRow])
    if (path === '/api/jobs/job-new') return respond(savedJob())
    if (path === '/api/jobs/job-old') return respond(savedJob(true))
    if (path === '/api/conversations/doc-new') return respond(detail(latest))
    if (path === '/api/conversations/doc-old') return respond(detail(older))
    if (path === '/api/conversations/doc-chat') return respond(detail(unassessed))
    return respond({detail: `Unmocked endpoint ${path}`}, 404)
  })
  return {writes, errors}
}

test('queue shows distinct conversations, latest results and explicit revision history', async ({page}) => {
  const {writes, errors} = await fixture(page)
  await page.goto('/')
  const queue = page.getByRole('complementary', {name: 'Список диалогов'})
  await expect(queue.locator('[data-testid^="queue-revision-"]')).toHaveCount(2)
  await expect(queue.getByRole('heading', {name: 'Диалоги', exact: true})).toBeVisible()
  await expect(page.getByTestId('queue-revision-doc-new').getByText('What fee applies?', {exact: true})).toBeVisible()
  await expect(page.getByTestId('queue-revision-doc-new').getByText('Идентификатор: call-1', {exact: true})).not.toBeVisible()
  await expect(page.getByTestId('queue-revision-doc-new')).toContainText('50/100')
  await expect(page.getByTestId('queue-revision-doc-new')).toContainText('Нужен пересмотр')
  await expect(page.getByTestId('queue-revision-doc-new')).toContainText('Открытых запросов: 1')
  await expect(page.getByTestId('queue-revision-doc-chat')).toContainText('Без оценки')
  await queue.getByLabel('Поиск диалогов').fill('fee applies')
  await expect(queue.locator('[data-testid^="queue-revision-"]')).toHaveCount(1)
  await expect(page.getByTestId('queue-revision-doc-new')).toBeVisible()
  await queue.getByLabel('Поиск диалогов').fill('call-1')
  await expect(queue.locator('[data-testid^="queue-revision-"]')).toHaveCount(1)
  await expect(page.getByTestId('queue-revision-doc-new')).toBeVisible()
  await queue.getByLabel('Поиск диалогов').fill('')
  await queue.getByLabel('Выбрать показанные', {exact: true}).check()
  await expect(page.getByRole('button', {name: 'Проверить выбранные', exact: true})).toBeVisible()
  await queue.getByRole('button', {name: 'История версий call-1'}).click()
  await expect(page.getByTestId('queue-revision-doc-new').getByText('Идентификатор: call-1', {exact: true})).toBeVisible()
  await expect(page.getByTestId('queue-revision-doc-old')).toBeVisible()
  await expect(page.getByTestId('queue-revision-doc-old').getByRole('checkbox')).not.toBeChecked()
  await page.getByRole('button', {name: 'Открыть оценку call-1, версия oldhash'}).click()
  await expect(page.getByTestId('score').locator('strong')).toHaveText('100')
  await queue.getByRole('button', {name: 'История версий call-1'}).click()
  await expect(page.getByTestId('queue-revision-doc-old')).toHaveCount(0)
  await expect(page).toHaveURL(/job=job-old/)
  await queue.getByRole('button', {name: 'Фильтры', exact: true}).click()
  await queue.getByLabel('Фильтр по статусу').selectOption('unassessed')
  await expect(queue.locator('[data-testid^="queue-revision-"]')).toHaveCount(1)
  await expect(page.getByTestId('queue-revision-doc-chat')).toBeVisible()
  expect(writes).toEqual([]); expect(errors).toEqual([])
})

test('scored appeal preserves uncertainty and requires explicit reason to clear it', async ({page}) => {
  const {writes, errors} = await fixture(page)
  async function openReview() {
    await page.goto('/?conversation=doc-new&job=job-new')
    await page.getByTestId('appeal-advice').getByRole('button', {name: 'Рассмотреть запрос'}).click()
    await page.getByLabel('Решение по запросу').selectOption('accept')
    await expect(page.getByLabel('Неподтверждённые сведения')).toHaveValue(uncertainty)
    await page.getByLabel('Имя проверяющего').fill('Synthetic reviewer')
    await page.getByLabel('Обоснование решения').fill('The selected source supports the retained grade.')
    await expect(page.getByLabel('Роль сообщения m2', {exact: true})).toHaveValue('')
    await page.getByLabel('Роль сообщения m3', {exact: true}).selectOption('support')
  }
  await openReview()
  await page.getByRole('checkbox', {name: /Я изучил критерий оценки/}).check()
  await page.getByRole('button', {name: 'Сохранить решение'}).click()
  await expect.poll(() => writes.length).toBe(1)
  expect(writes[0].body.judgment).toMatchObject({status: 'scored', answer: '5', uncertainty, evidence: [{message_id: 'm3', quote: messages[2].text}]})

  await openReview()
  await page.getByLabel('Неподтверждённые сведения').fill('')
  await page.getByRole('checkbox', {name: /Я изучил критерий оценки/}).check()
  await expect(page.getByRole('button', {name: 'Сохранить решение'})).toBeDisabled()
  await page.getByLabel('Подтвердить проверку недостающих сведений').check()
  await page.getByRole('checkbox', {name: /Я изучил критерий оценки/}).check()
  await expect(page.getByRole('button', {name: 'Сохранить решение'})).toBeDisabled()
  await page.getByLabel('Обоснование снятия замечания').fill('The reviewer checked the applicable tariff and recorded the source basis.')
  await page.getByRole('checkbox', {name: /Я изучил критерий оценки/}).check()
  await page.getByRole('button', {name: 'Сохранить решение'}).click()
  await expect.poll(() => writes.length).toBe(2)
  expect(writes[1].body.judgment).toMatchObject({status: 'scored', answer: '5', uncertainty: null})
  expect(writes[1].body.rationale).toContain('Недостающие сведения проверены: The reviewer checked the applicable tariff')
  expect(errors).toEqual([])
})

test('call revision edit/import retains the original recording URL', async ({page}) => {
  const {writes, errors} = await fixture(page)
  await page.goto('/?conversation=doc-new')
  await page.getByText('Сведения о диалоге', {exact: true}).click()
  await page.getByRole('button', {name: 'Создать копию', exact: true}).click()
  const dialog = page.getByRole('dialog', {name: 'Загрузить данные', exact: true})
  await expect(dialog).toBeVisible()
  const input = JSON.parse(await dialog.getByLabel('Диалоги в формате JSON').inputValue())
  expect(input.recording_url).toBe(recording)
  expect(input.messages).toEqual(messages)
  input.messages[2].text += ' Revised transcript punctuation.'
  await dialog.getByLabel('Диалоги в формате JSON').fill(JSON.stringify(input))
  await dialog.getByRole('button', {name: 'Загрузить', exact: true}).click()
  await expect.poll(() => writes.length).toBe(1)
  expect(writes[0].path).toBe('/api/conversations/import')
  expect(JSON.parse(String(writes[0].body.content))).toMatchObject({recording_url: recording, id: 'call-1'})
  expect(errors).toEqual([])
})

test('reselecting a conversation keeps its result and cancelling review setup writes nothing', async ({page}) => {
  const {writes, errors} = await fixture(page)
  await page.goto('/')
  const row = page.getByTestId('queue-revision-doc-new')
  const choose = row.getByRole('button', {name: 'What fee applies? Звонок · EN · Сообщений: 3', exact: true})
  await choose.click()
  await expect(page.getByTestId('score').locator('strong')).toHaveText('50')
  await choose.click()
  await expect(page.getByTestId('score').locator('strong')).toHaveText('50')
  await expect(page.getByRole('heading', {name: 'What fee applies?', exact: true})).toBeVisible()

  await page.getByRole('button', {name: 'Параметры проверки', exact: true}).click()
  const setup = page.getByRole('dialog', {name: 'Начать проверку', exact: true})
  await expect(setup.getByLabel('Чек-лист для проверки')).toHaveValue(checklist.id)
  await setup.getByText('Параметры проверки', {exact: true}).click()
  await setup.getByLabel('Лимит расходов на проверку').fill('0.25')
  await setup.getByRole('button', {name: 'Отмена', exact: true}).click()
  await expect(setup).toHaveCount(0)

  await page.getByText('Сведения и выгрузка', {exact: true}).click()
  await page.getByRole('button', {name: 'Проверить ещё раз', exact: true}).click()
  const retry = page.getByRole('dialog', {name: 'Повторить проверку', exact: true})
  await expect(retry.getByLabel('Лимит расходов на проверку')).toBeVisible()
  await expect(retry.getByLabel('Лимит расходов на проверку')).toHaveValue('0.25')
  await expect(retry).toContainText('Исходный чек-лист: Synthetic QA')
  await retry.getByRole('button', {name: 'Отмена', exact: true}).click()
  await expect(retry).toHaveCount(0)
  await expect(page.getByTestId('score').locator('strong')).toHaveText('50')
  expect(writes).toEqual([]); expect(errors).toEqual([])
})
