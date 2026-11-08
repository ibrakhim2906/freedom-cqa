import {test, expect} from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

// This writes checklist versions. Opt in only against an isolated application database.
// It never starts an evaluation and reuses existing completed jobs solely for preservation checks.
test.skip(process.env.CQA_JUDGE_E2E !== '1', 'Explicit isolated judge-workflow opt-in required')
test.use({baseURL: process.env.CQA_JUDGE_BASE_URL || 'http://127.0.0.1:8012', actionTimeout: 15000})

test('UI adds, deletes and reweights criteria while preserving historical results', async ({page, request}, testInfo) => {
  const nonce = String(Date.now()), errors: string[] = [], evaluationRequests: string[] = []
  const output = path.resolve(`../artifacts/release-hardening/judge-checklist-${nonce}`)
  fs.mkdirSync(output, {recursive: true})
  page.on('pageerror', error => errors.push(error.message))
  await page.route('**/api/evaluations', async route => {
    evaluationRequests.push(route.request().method())
    await route.abort()
  })
  const configBefore = await (await request.get('/api/config')).json()
  const listsBefore = await (await request.get('/api/checklists')).json()
  const jobsBefore = await (await request.get('/api/jobs')).json()
  const preservedJobs = await Promise.all(jobsBefore.map(async (job: {id: string}) =>
    await (await request.get(`/api/jobs/${job.id}`)).json()))
  const source = preservedJobs.find(job => job.status === 'completed'
    && job.checklist.external_id.startsWith('release-rules-') && job.checklist.content.criteria.length === 2)
  expect(source, 'The isolated store must contain the real custom-rule workflow result').toBeTruthy()
  const original = listsBefore.find((row: {external_id: string}) => row.external_id === source.checklist.external_id)
  const updatedWeight = original.content.criteria[0].weight + 7
  const version = `judge-ui-${nonce}`, title = `Проверка критериев через интерфейс ${nonce}`

  await page.goto('/')
  await page.getByRole('button', {name: 'Критерии оценки', exact: true}).click()
  await page.getByLabel('Выбор чек-листа').selectOption(original.id)
  await page.getByRole('button', {name: 'Создать копию', exact: true}).click()
  await page.getByLabel('Название чек-листа', {exact: true}).fill(title)
  const form = page.locator('form').filter({has: page.getByLabel('Название чек-листа', {exact: true})})
  await form.locator('summary').filter({hasText: /^Технические сведения$/}).first().click()
  await form.getByLabel('ID чек-листа', {exact: true}).fill(original.external_id)
  await form.getByLabel('Версия', {exact: true}).fill(version)

  await form.locator('summary').filter({hasText: `1. ${original.content.criteria[0].title}`}).click()
  const first = form.getByRole('group', {name: 'Критерий 1', exact: true})
  const instruction = 'Оператор явно представился личным именем в собственном сообщении. Имя клиента не засчитывается.'
  const updatedInstruction = original.content.criteria[0].instruction === instruction
    ? 'Оператор явно представился личным именем в первом собственном сообщении. Позднее представление и имя клиента не засчитываются.'
    : instruction
  expect(updatedInstruction).not.toBe(original.content.criteria[0].instruction)
  await first.getByLabel('Критерий 1: по каким признакам оценивать выполнение', {exact: true}).fill(updatedInstruction)
  await first.getByLabel('Максимум баллов', {exact: true}).fill(String(updatedWeight))
  await expect(first.getByLabel('Критерий 1: баллы за ответ 1', {exact: true})).toHaveValue(String(updatedWeight))

  await form.getByRole('button', {name: 'Добавить критерий', exact: true}).first().click()
  const added = form.getByRole('group', {name: 'Критерий 3', exact: true})
  await added.getByLabel('Критерий 3: название критерия', {exact: true}).fill('Следующий шаг для клиента')
  await added.getByLabel('Критерий 3: по каким признакам оценивать выполнение', {exact: true})
    .fill('Оператор объяснил, какое действие клиенту необходимо выполнить следующим.')
  await added.getByLabel('Максимум баллов', {exact: true}).fill('5')
  await form.locator('summary').filter({hasText: `2. ${original.content.criteria[1].title}`}).click()
  await form.getByRole('group', {name: 'Критерий 2', exact: true})
    .getByRole('button', {name: 'Удалить критерий', exact: true}).click()
  await expect(form.getByRole('group', {name: /^Критерий \d+$/})).toHaveCount(2)

  const saving = page.waitForResponse(response => response.url().endsWith('/api/checklists')
    && response.request().method() === 'POST')
  await form.getByRole('button', {name: 'Сохранить чек-лист', exact: true}).click()
  const response = await saving
  expect(response.status()).toBe(200)
  const submitted = response.request().postDataJSON()
  const {created, ...saved} = await response.json()
  expect(created).toBe(true)
  expect(saved.id).not.toBe(original.id)
  expect(saved.external_id).toBe(original.external_id)
  expect(saved.version).toBe(version)
  expect(saved.content).toMatchObject(submitted)
  expect(saved.content.criteria).toHaveLength(2)
  expect(saved.content.criteria.map((criterion: {weight: number}) => criterion.weight)).toEqual([updatedWeight, 5])
  expect(saved.content.criteria[0].instruction).toBe(updatedInstruction)
  expect(saved.content.criteria[0].levels).toEqual(original.content.criteria[0].levels)
  expect(saved.content.criteria[1].title).toBe('Следующий шаг для клиента')
  expect(saved.content.criteria.some((criterion: {id: string}) => criterion.id === original.content.criteria[1].id)).toBe(false)
  await expect(page.getByLabel('Выбор чек-листа')).toHaveValue(saved.id)
  await page.screenshot({path: path.join(output, 'saved-edited-checklist.png'), fullPage: true})

  await page.goto(`/?conversation=${source.conversation_id}&job=${source.id}`)
  await expect(page.getByTestId('job-status')).toHaveAttribute('data-status', 'completed')
  await page.getByRole('button', {name: 'Параметры проверки', exact: true}).first().click()
  const setup = page.getByRole('dialog', {name: 'Начать проверку', exact: true})
  await setup.getByLabel('Чек-лист для проверки').selectOption(saved.id)
  await expect(setup.getByLabel('Чек-лист для проверки')).toHaveValue(saved.id)
  await page.screenshot({path: path.join(output, 'new-version-available.png'), fullPage: true})

  const listsAfter = await (await request.get('/api/checklists')).json()
  expect(listsAfter.find((row: {id: string}) => row.id === saved.id)).toEqual(saved)
  for (const previous of listsBefore) {
    expect(listsAfter.find((row: {id: string}) => row.id === previous.id)).toEqual(previous)
  }
  expect(await (await request.get('/api/jobs')).json()).toEqual(jobsBefore)
  for (const previous of preservedJobs) {
    expect(await (await request.get(`/api/jobs/${previous.id}`)).json()).toEqual(previous)
  }
  const configAfter = await (await request.get('/api/config')).json()
  expect(configAfter.ledger.lifetime_committed_usd).toBe(configBefore.ledger.lifetime_committed_usd)
  expect(configAfter.ledger.attempts_by_status).toEqual(configBefore.ledger.attempts_by_status)
  expect(evaluationRequests).toEqual([])
  expect(errors).toEqual([])
  const receipt = {at_utc: new Date().toISOString(), original_checklist_id: original.id,
    saved_checklist_id: saved.id, external_id: saved.external_id, saved_version: saved.version,
    previous_first_weight: original.content.criteria[0].weight, saved_weights: [updatedWeight, 5],
    criterion_added: true, criterion_deleted: true,
    instruction_edited: true, selected_version_available: true,
    prior_checklists_preserved: listsBefore.length, prior_job_snapshots_preserved: preservedJobs.length,
    new_evaluations: 0, model_spend_delta_usd: 0, browser_errors: errors}
  fs.writeFileSync(path.join(output, 'receipt.json'), JSON.stringify(receipt, null, 2))
  await testInfo.attach('checklist-edit-receipt', {body: JSON.stringify(receipt, null, 2), contentType: 'application/json'})
})
