import {test, expect} from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

// Intentionally opt-in: the default test command cannot silently spend API credits.
test.skip(process.env.CQA_LIVE_E2E !== '1', 'Set CQA_LIVE_E2E=1 to authorize the real local-API walkthrough')
const artifacts = path.resolve('../artifacts/workflow-validation')
fs.mkdirSync(artifacts, {recursive: true})
const stateFile = path.join(artifacts, 'browser-state.json')
type State = {nonce: string; conversationId?: string; jobId?: string; customChecklistId?: string; customJobId?: string; failureJobId?: string; initialCommitted?: number}
const state: State = fs.existsSync(stateFile) ? JSON.parse(fs.readFileSync(stateFile, 'utf8')) : {nonce: String(Date.now())}
const save = () => fs.writeFileSync(stateFile, JSON.stringify(state, null, 2))
save()

test('real import → evaluate → evidence → appeal → persistence → custom checklist', async ({page, request}) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  const initialConfig = await (await request.get('/api/config')).json()
  expect(initialConfig.api_key_configured).toBeTruthy()
  if (state.initialCommitted === undefined) {state.initialCommitted = initialConfig.ledger.lifetime_committed_usd; save()}
  await page.goto('/')
  await expect(page.getByText('API configured', {exact: true})).toBeVisible()
  if (!state.conversationId) {
    const cases = fs.readFileSync(path.resolve('../evals/targeted-v5.jsonl'), 'utf8').trim().split('\n').map(s => JSON.parse(s))
    const conversation = cases.find(c => c.id === 'facts-profile-missing').conversation
    conversation.id = `workflow-live-${state.nonce}`
    await page.getByRole('button', {name: 'Import conversations', exact: true}).click()
    await page.getByLabel('Conversation file').setInputFiles({name: 'new-conversation.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(conversation))})
    const imported = page.waitForResponse(r => r.url().endsWith('/api/conversations/import') && r.request().method() === 'POST')
    await page.getByRole('button', {name: 'Import', exact: true}).click()
    const response = await imported
    expect(response.status()).toBe(200)
    state.conversationId = (await response.json()).conversations[0].id; save()
  } else await page.goto(`/?conversation=${state.conversationId}`)
  await expect(page.getByRole('button', {name: 'Evaluate this revision', exact: true})).toBeVisible()
  if (!state.jobId) {
    const submitted = page.waitForResponse(r => r.url().endsWith('/api/evaluations') && r.request().method() === 'POST')
    await page.getByRole('button', {name: 'Evaluate this revision', exact: true}).click()
    const response = await submitted
    expect(response.status()).toBe(202)
    state.jobId = (await response.json()).job_ids[0]; save()
  }
  await page.goto(`/?conversation=${state.conversationId}&job=${state.jobId}`)
  await expect(page.getByTestId('job-status')).toHaveText('completed', {timeout: 130000})
  const original = await (await request.get(`/api/jobs/${state.jobId}`)).json()
  expect(original.record.response_id).toMatch(/^resp_/)
  expect(original.record.model).toBe('gpt-6.1-sol')
  expect(original.record.usage.estimated_cost_usd).toBeGreaterThan(0)
  expect(original.record.score.provisional).toBeTruthy()
  const consultation = page.getByTestId('criterion-consultation')
  await consultation.getByRole('button', {name: /^m2:/}).first().click()
  await expect(page.locator('#message-m2 mark')).toBeVisible()
  await page.screenshot({path: path.join(artifacts, 'source-evidence.png'), fullPage: true})
  if (!original.appeals.some((a: {criterion_id: string; status: string}) => a.criterion_id === 'consultation' && a.status === 'accepted')) {
    if (!original.appeals.some((a: {status: string}) => a.status === 'open')) {
      await consultation.getByRole('button', {name: 'Appeal this judgment'}).click()
      await page.getByLabel('Appeal author').fill('Workflow validation operator')
      await page.getByLabel('Appeal reason').fill('The official profile-update guide verifies this route for the declared platform and date. Please review with that source.')
      await page.getByRole('checkbox', {name: /^m2 · operator:/}).check()
      await page.getByRole('button', {name: 'Submit appeal', exact: true}).click()
    }
    await page.getByTestId('appeal-consultation').getByRole('button', {name: 'Review appeal'}).click()
    await page.getByLabel('Appeal decision').selectOption('accept')
    await page.getByLabel('Reviewed status').selectOption('scored')
    await page.getByLabel('Reviewed answer').selectOption('20')
    await page.getByLabel('Reviewer name').fill('QA workflow validation')
    await page.getByLabel('Decision rationale').fill('Verified against the official fbroker.kz profile-update guide, valid for the declared fbroker-kz-platform context on 2026-11-07. The selected source gives the same mobile navigation path.')
    await page.getByLabel('Use message m2', {exact: true}).selectOption('support')
    await page.getByRole('checkbox', {name: /^fbroker-profile-20261107/}).check()
    await page.getByRole('checkbox', {name: /I reviewed the criterion/}).check()
    await page.getByRole('button', {name: 'Save review decision', exact: true}).click()
  }
  await expect(page.getByTestId('score')).toContainText('Human-reviewed')
  const reviewed = await (await request.get(`/api/jobs/${state.jobId}`)).json()
  expect(reviewed.record).toEqual(original.record)
  expect(reviewed.effective.score.total).toBe(100)
  expect(reviewed.appeals.find((a: {status: string}) => a.status === 'accepted').resolution.supporting_references[0].id).toBe('fbroker-profile-20261107')
  await page.getByRole('button', {name: 'Review source: fbroker-profile-20261107'}).click()
  await expect(page.getByRole('button', {name: 'Close reference'})).toBeVisible()
  await page.getByRole('button', {name: 'Close reference'}).click()
  const beforeCache = (await (await request.get('/api/config')).json()).ledger.lifetime_committed_usd
  const cached = page.waitForResponse(r => r.url().endsWith('/api/evaluations') && r.request().method() === 'POST')
  await page.getByRole('button', {name: 'Evaluate this revision', exact: true}).click()
  expect((await (await cached).json()).reused).toContain(state.jobId)
  await page.reload()
  await expect(page.getByTestId('score')).toContainText('Human-reviewed')
  expect((await (await request.get('/api/config')).json()).ledger.lifetime_committed_usd).toBe(beforeCache)
  await page.screenshot({path: path.join(artifacts, 'reviewed-result.png'), fullPage: true})

  if (!state.customChecklistId) {
    await page.getByRole('button', {name: 'Checklists', exact: true}).click()
    await page.getByRole('button', {name: 'New checklist', exact: true}).click()
    await page.getByLabel('Checklist ID', {exact: true}).fill(`workflow-checklist-${state.nonce}`)
    await page.getByLabel('Title', {exact: true}).first().fill('Workflow named introduction')
    const criterion = page.getByRole('group', {name: 'Criterion 1', exact: true})
    await criterion.getByLabel('ID', {exact: true}).fill('named-introduction')
    await criterion.getByLabel('Title', {exact: true}).fill('Named human introduction')
    await page.getByLabel('Criterion 1 instruction').fill('Assess only whether the HUMAN operator explicitly introduced themselves with a personal name. Use introduced when present, absent otherwise. Bot introductions do not count. This criterion assesses the spoken or written introduction, not external identity verification.')
    await page.getByLabel('Criterion 1 level 1 value').fill('introduced')
    await page.getByLabel('Criterion 1 level 1 description').fill('The human explicitly gives their name in a self-introduction.')
    await page.getByLabel('Criterion 1 level 2 value').fill('absent')
    await page.getByLabel('Criterion 1 level 2 description').fill('No human name is given in a self-introduction.')
    const saved = page.waitForResponse(r => r.url().endsWith('/api/checklists') && r.request().method() === 'POST')
    await page.getByRole('button', {name: 'Save checklist version'}).click()
    const response = await saved
    expect(response.status()).toBe(200)
    state.customChecklistId = (await response.json()).id; save()
  }
  await page.getByRole('button', {name: 'Conversations', exact: true}).click()
  await page.getByLabel('Evaluation checklist').selectOption(state.customChecklistId!)
  if (!state.customJobId) {
    const submitted = page.waitForResponse(r => r.url().endsWith('/api/evaluations') && r.request().method() === 'POST')
    await page.getByRole('button', {name: 'Evaluate this revision', exact: true}).click()
    state.customJobId = (await (await submitted).json()).job_ids[0]; save()
  }
  await page.goto(`/?conversation=${state.conversationId}&job=${state.customJobId}`)
  await expect(page.getByTestId('job-status')).toHaveText('completed', {timeout: 130000})
  await expect(page.getByTestId('criterion-named-introduction')).toContainText('introduced')
  const custom = await (await request.get(`/api/jobs/${state.customJobId}`)).json()
  expect(custom.checklist.content.criteria).toHaveLength(1)
  expect(custom.record.evaluation.judgments[0].answer).toBe('introduced')
  const exported = await request.get(`/api/jobs/${state.jobId}/export`)
  expect((await exported.json()).record).toEqual(original.record)
  await page.goto(`/?conversation=${state.conversationId}&job=${state.jobId}`)
  await expect(page.getByTestId('score')).toContainText('Human-reviewed')
  const finalConfig = await (await request.get('/api/config')).json()
  fs.writeFileSync(path.join(artifacts, 'report.json'), JSON.stringify({
    tested: ['file import', 'real evaluator', 'source evidence navigation', 'appeal', 'reference-backed acceptance',
      'immutable AI result', 'human score recalculation', 'cached reuse without API spend', 'page reload',
      'new runtime checklist through UI and real API', 'export'],
    conversation_id: state.conversationId, job_id: state.jobId, custom_job_id: state.customJobId,
    original_total: original.record.score.total, reviewed_total: reviewed.effective.score.total,
    cost_usd: Number((finalConfig.ledger.lifetime_committed_usd - state.initialCommitted!).toFixed(6)),
    this_run_cost_usd: Number((finalConfig.ledger.lifetime_committed_usd - initialConfig.ledger.lifetime_committed_usd).toFixed(6)),
    browser_errors: errors, ledger: finalConfig.ledger,
  }, null, 2))
  expect(errors).toEqual([])
})

test('budget exhaustion shows a real failure with no replacement score', async ({page, request}) => {
  test.skip(!state.jobId, 'Complete the real evaluation walkthrough first')
  const before = (await (await request.get('/api/config')).json()).ledger.lifetime_committed_usd
  await page.goto(`/?conversation=${state.conversationId}&job=${state.jobId}`)
  await expect(page.getByTestId('job-status')).toHaveText('completed')
  if (!state.failureJobId) {
    await page.getByLabel('Batch budget').fill('0.0001')
    const submitted = page.waitForResponse(r => r.url().endsWith('/retry') && r.request().method() === 'POST')
    await page.getByRole('button', {name: 'Run again (billable)', exact: true}).click()
    state.failureJobId = (await (await submitted).json()).job_ids[0]; save()
  }
  await page.goto(`/?conversation=${state.conversationId}&job=${state.failureJobId}`)
  await expect(page.getByTestId('job-status')).toHaveText('failed')
  await expect(page.getByRole('alert')).toContainText('budget_limit')
  await expect(page.getByTestId('score')).toHaveCount(0)
  await expect(page.getByRole('button', {name: 'Retry (billable)', exact: true})).toBeVisible()
  expect((await (await request.get('/api/config')).json()).ledger.lifetime_committed_usd).toBe(before)
  const original = await (await request.get(`/api/jobs/${state.jobId}`)).json()
  expect(original.status).toBe('completed')
  expect(original.effective.source).toBe('human_review')
  await page.screenshot({path: path.join(artifacts, 'budget-failure.png'), fullPage: true})
  await page.goto(`/?conversation=${state.conversationId}&job=${state.jobId}`)
  await expect(page.getByTestId('score')).toContainText('Human-reviewed')
  fs.writeFileSync(path.join(artifacts, 'failure-report.json'), JSON.stringify({failure_job: state.failureJobId,
    provider_spend_delta: 0, preserved_original_job: state.jobId, status: 'passed'}, null, 2))
})
