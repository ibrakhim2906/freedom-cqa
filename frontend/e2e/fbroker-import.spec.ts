import {test, expect} from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

test.use({baseURL: process.env.CQA_UI_BASE_URL || 'http://127.0.0.1:8014'})
test('one-click FBroker setup selects all imported chats without starting analysis', async ({page}) => {
  const content = JSON.parse(fs.readFileSync(path.resolve('..', 'checklists/freedom-reviewed-018.json'), 'utf8'))
  const checklist = {id: 'main-doc', external_id: content.id, version: content.version, title: content.title, content_hash: 'main-hash', content}
  const messages = [{id: 'm1', timestamp: '00:01', speaker: 'client', text: 'Pricing?'}]
  const rows = [1, 2, 3].map(i => ({id: `doc-${i}`, external_id: `fresh-${i}`, content_hash: `hash-${i}`, created_at: '2026-11-08T06:00:00Z', channel: 'agent chat', language: 'EN', message_count: 1, reference_count: 9, latest_assessment: null}))
  let imported = false
  const writes: {path: string; body: Record<string, unknown>}[] = []
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  await page.route('**/api/**', route => {
    const request = route.request(), pathname = new URL(request.url()).pathname
    const reply = (json: unknown, status = 200) => route.fulfill({json, status})
    if (request.method() !== 'GET') {
      writes.push({path: pathname, body: request.postDataJSON()})
      if (pathname === '/api/conversations/import') {imported = true; return reply({created: 3, reused: 0, conversations: rows})}
      return reply({detail: 'Unexpected write blocked'}, 403)
    }
    if (pathname === '/api/config') return reply({import_presets: ['fbroker'], api_key_configured: false, model: 'fixture', strategy: 'assessor', default_checklist: {id: content.id, version: content.version}, ledger: {lifetime_committed_usd: 0, lifetime_limit_usd: 1}})
    if (pathname === '/api/checklists') return reply([checklist])
    if (pathname === '/api/conversations') return reply(imported ? rows : [])
    if (pathname === '/api/reference-packs') return reply([])
    if (pathname.endsWith('/evidence-context')) return reply({temporal: {occurred_on: null, origin: 'unknown', has_conflict: false}, assessment: {conditional: true, scope: 'freedom-finance-global-platform', as_of: '2026-11-07', rationale: 'Preset'}, references: []})
    const row = rows.find(r => pathname === `/api/conversations/${r.id}`)
    if (row) return reply({...row, content: {id: row.external_id, channel: row.channel, language: row.language, messages, references: []}, metadata: {}})
    return reply([])
  })
  await page.goto('/')
  await page.getByRole('button', {name: 'Загрузить данные', exact: true}).first().click()
  await page.getByRole('button', {name: 'Загрузить файл', exact: true}).click()
  await page.getByLabel('Файл с диалогами').setInputFiles({name: 'fbroker.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify({isSuccess: true, data: {dataset_group_id: 'FBroker', records: []}}))})
  await page.getByRole('button', {name: 'Загрузить FBroker с документами', exact: true}).click()
  await expect(page.getByText(/FBroker загружен: 3 диалогов/)).toBeVisible()
  await page.getByRole('button', {name: 'Проверить выбранные', exact: true}).click()
  await expect(page.getByRole('heading', {name: 'Проверка диалогов: 3', exact: true})).toBeVisible()
  expect(writes).toHaveLength(1)
  expect(writes[0].body.reference_preset).toBe('fbroker')
  expect(errors).toEqual([])
})
