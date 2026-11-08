import {test, expect} from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

// Opt-in paid test. Use a separate application database; never run against the team's saved workspace.
test.skip(process.env.CQA_RELEASE_LIVE !== '1', 'Explicit paid release-workflow opt-in required')
test.use({baseURL: process.env.CQA_RELEASE_BASE_URL || 'http://127.0.0.1:8012', actionTimeout: 15000})
test.setTimeout(240000)

test('Russian workflow applies changed rules and preserves actual model results', async ({page, request}) => {
  const output = path.resolve('../artifacts/release-hardening/live-workflow')
  fs.mkdirSync(output, {recursive: true})
  const stateFile = path.join(output, 'browser-state.json')
  const state = fs.existsSync(stateFile) ? JSON.parse(fs.readFileSync(stateFile, 'utf8')) : {nonce: String(Date.now())}
  fs.writeFileSync(stateFile, JSON.stringify(state))
  const nonce = state.nonce, errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  const initial = await (await request.get('/api/config')).json()
  expect(initial.api_key_configured).toBe(true)
  const levels = [{value: 'yes', fraction: 1, description: 'Требование выполнено.'},
    {value: 'no', fraction: 0, description: 'Требование не выполнено.'}]
  const checklist = {id: `release-rules-${nonce}`, version: '1', title: 'Проверка имени и срока',
    instructions: ['Оценивайте только явные слова оператора. Эти критерии не проверяют исполнение обещания.'], criteria: [
      {id: 'name', title: 'Имя оператора', instruction: 'Оператор явно представился личным именем.', kind: 'binary', weight: 10, levels},
      {id: 'deadline', title: 'Срок ответа', instruction: 'Оператор назвал срок ответа. Относительный срок «завтра» достаточен; календарная дата не требуется.', kind: 'binary', weight: 10, levels}]}
  const saved = await request.post('/api/checklists', {data: checklist})
  expect(saved.ok()).toBe(true)
  const firstChecklist = await saved.json()
  await page.goto('/')
  await page.getByRole('button', {name: 'Загрузить данные', exact: true}).first().click()
  const importing = page.getByRole('dialog', {name: 'Загрузить данные', exact: true})
  await importing.getByLabel('Текст диалога', {exact: true}).fill(
    'Клиент: Когда вы ответите на моё обращение?\nОператор: Добрый день! Я Алия. Я проверю обращение и отвечу завтра.\nКлиент: Спасибо, буду ждать.')
  const imported = page.waitForResponse(r => r.url().endsWith('/api/conversations/import') && r.request().method() === 'POST')
  await importing.getByRole('button', {name: 'Добавить диалог', exact: true}).click()
  const conversationId = (await (await imported).json()).conversations[0].id
  const source = await (await request.get(`/api/conversations/${conversationId}`)).json()
  expect(source.content.messages).toHaveLength(3)
  expect(source.content.messages.map((m: {speaker: string}) => m.speaker)).toEqual(['client', 'operator', 'client'])
  expect(source.content.messages.every((m: {timestamp: string}) => m.timestamp === '')).toBe(true)

  async function evaluate(checklistId: string) {
    const savedJobs = await (await request.get(`/api/jobs?conversation_id=${conversationId}`)).json()
    const previous = savedJobs.find((job: {status: string; checklist_id: string}) => job.status === 'completed' && job.checklist_id === checklistId)
    if (previous) {
      await page.goto(`/?conversation=${conversationId}&job=${previous.id}`)
      await expect(page.getByTestId('job-status')).toHaveAttribute('data-status', 'completed')
      return await (await request.get(`/api/jobs/${previous.id}`)).json()
    }
    await page.goto(`/?conversation=${conversationId}`)
    const setupButton = page.getByRole('button', {name: /^(Начать проверку|Параметры проверки)$/}).first()
    await setupButton.click()
    const dialog = page.getByRole('dialog', {name: 'Начать проверку', exact: true})
    await dialog.getByLabel('Чек-лист для проверки').selectOption(checklistId)
    await dialog.locator('summary').filter({hasText: 'Параметры проверки'}).click()
    await dialog.getByLabel('Лимит расходов на проверку').fill('0.15')
    const submitted = page.waitForResponse(r => r.url().endsWith('/api/evaluations') && r.request().method() === 'POST')
    await dialog.getByRole('button', {name: 'Начать проверку', exact: true}).click()
    const response = await submitted
    expect(response.status()).toBe(202)
    const id = (await response.json()).job_ids[0]
    await expect.poll(async () => (await (await request.get(`/api/jobs/${id}`)).json()).status,
      {timeout: 140000, intervals: [1000, 2000]}).toBe('completed')
    await page.goto(`/?conversation=${conversationId}&job=${id}`)
    await expect(page.getByTestId('job-status')).toHaveAttribute('data-status', 'completed')
    return await (await request.get(`/api/jobs/${id}`)).json()
  }
  const first = await evaluate(firstChecklist.id)
  expect(first.record.response_id).toMatch(/^resp_/)
  expect(first.record.score.total).toBe(100)
  expect(first.record.evaluation.judgments.map((j: {answer: string}) => j.answer)).toEqual(['yes', 'yes'])
  const revised = structuredClone(checklist)
  revised.version = '2'
  revised.criteria[1].instruction = 'Оператор явно назвал календарную дату ответа: день, месяц и год. Относительный срок «завтра» недостаточен. Если календарной даты нет, ответ no. Это проверка формата обещанного срока, а не его исполнения.'
  const updated = await request.post('/api/checklists', {data: revised})
  expect(updated.ok()).toBe(true)
  const secondChecklist = await updated.json()
  const second = await evaluate(secondChecklist.id)
  expect(second.record.response_id).toMatch(/^resp_/)
  expect(second.record.response_id).not.toBe(first.record.response_id)
  expect(second.record.score.total).toBe(50)
  expect(second.record.evaluation.judgments.find((j: {criterion_id: string}) => j.criterion_id === 'deadline').answer).toBe('no')
  await expect(page.getByRole('meter')).toHaveAttribute('aria-valuenow', '50')
  const name = page.getByTestId('criterion-name')
  await name.locator('summary').filter({hasText: 'Обоснование и цитаты'}).click()
  await name.getByRole('button', {name: /^m2:/}).first().click()
  await expect(page.locator('#message-m2 mark').first()).toBeVisible()
  await page.screenshot({path: path.join(output, 'exact-evidence.png'), fullPage: true})
  await page.getByRole('button', {name: 'Результат проверки', exact: true}).click()
  await page.getByTestId('criterion-deadline').locator('summary').filter({hasText: 'Обоснование и цитаты'}).click()
  await page.getByTestId('criterion-deadline').getByRole('button', {name: 'Запросить пересмотр', exact: true}).click()
  const appeal = page.getByRole('dialog', {name: 'Запросить пересмотр', exact: true})
  await appeal.getByLabel('Имя автора запроса').fill('Изолированная проверка рабочего процесса')
  await appeal.getByLabel('Причина пересмотра').fill('Прошу проверить, достаточно ли относительного срока по сохранённой версии правила.')
  await appeal.getByRole('checkbox', {name: /^m2 ·/}).check()
  await appeal.getByRole('button', {name: 'Отправить запрос', exact: true}).click()
  await page.getByTestId('appeal-deadline').getByRole('button', {name: 'Рассмотреть запрос'}).click()
  const review = page.getByRole('dialog', {name: 'Запрос на пересмотр', exact: true})
  await review.getByLabel('Имя проверяющего').fill('Проверка релиза')
  await review.getByLabel('Обоснование решения').fill('В версии 2 явно требуется календарная дата с годом. В сообщении m2 есть только «завтра», поэтому исходная оценка соответствует правилу.')
  await review.getByRole('checkbox', {name: /^Я изучил критерий оценки/}).check()
  await review.getByRole('button', {name: 'Сохранить решение', exact: true}).click()
  await expect(review).toHaveCount(0)
  await page.reload()
  const exported = await (await request.get(`/api/jobs/${second.id}/export`)).json()
  expect(exported.record).toEqual(second.record)
  expect(exported.appeals[0].status).toBe('rejected')
  expect(exported.checklist.content).toEqual(second.checklist.content)
  expect((await (await request.get(`/api/jobs/${first.id}`)).json()).record).toEqual(first.record)
  const beforeCache = (await (await request.get('/api/config')).json()).ledger.lifetime_committed_usd
  const cached = await request.post('/api/evaluations', {data: {conversation_ids: [conversationId],
    checklist_id: secondChecklist.id, request_id: `release-cache-${nonce}`, budget_usd: 0.15}})
  expect((await cached.json()).reused).toContain(second.id)
  const final = await (await request.get('/api/config')).json()
  expect(final.ledger.lifetime_committed_usd).toBe(beforeCache)
  expect(errors).toEqual([])
  fs.writeFileSync(path.join(output, `receipt-${nonce}.json`), JSON.stringify({conversation_id: conversationId,
    first_job: first.id, second_job: second.id, totals: [100, 50], model_cost_usd: [first, second].reduce(
      (sum, job) => sum + job.record.usage.estimated_cost_usd, 0), cache_spend_delta: 0,
    source_roles_preserved: true, fabricated_timestamps: false, original_results_preserved: true,
    appeal_retained_after_reload: true, browser_errors: errors}, null, 2))
  await page.screenshot({path: path.join(output, 'reviewed-workflow.png'), fullPage: true})
})
