import test from 'node:test'
import assert from 'node:assert/strict'
import {currentChecklistId, visibleChecklists} from '../src/checklistCatalog.ts'

const row = (id, external_id, title, created_at, version = '1') => ({
  id, external_id, title, created_at, version, content_hash: id,
  content: {id: external_id, title, version, instructions: [], criteria: []},
})
const main = row('main-new', 'main', 'Main grading checklist', '2026-11-08T08:00:00Z', 'reviewed-016')
const mainOld = row('main-old', 'main', 'Old main name', '2026-11-07T08:00:00Z', 'reviewed-015')
const personal = row('mine', 'personal-1', 'My support checklist', '2026-11-08T09:00:00Z')

test('normal catalogue excludes known validation records and keeps the main checklist first', () => {
  const fixtures = ['delivery-unseen-handoff', 'delivery-followup-contract', 'fresh-keyboard-review', 'workflow-checklist-1794051744741']
    .map(id => row(id, id, 'Test checklist', '2026-11-08T10:00:00Z'))
  const saved = [...fixtures, personal, mainOld, main]
  assert.deepEqual(visibleChecklists(saved, 'main').map(c => c.id), ['main-new', 'mine'])
  assert.equal(saved.length, 7, 'historical records must remain available')
})

test('latest saved date wins even when version labels do not sort numerically', () => {
  const newest = row('mine-new', 'personal-1', 'Updated support checklist', '2026-11-08T11:00:00Z', 'edited')
  assert.deepEqual(visibleChecklists([personal, newest, mainOld, main], 'main').map(c => c.id), ['main-new', 'mine-new'])
})

test('user checklists with test-like names or IDs are not hidden', () => {
  const sameTitle = row('mine-2', 'checklist-123', 'Configured handoff review', '2026-11-08T11:00:00Z')
  const similarId = row('mine-3', 'workflow-checklist-123', 'My keyboard checklist', '2026-11-08T11:00:00Z')
  const result = visibleChecklists([sameTitle, similarId, main], 'main')
  assert.deepEqual(new Set(result.map(c => c.id)), new Set(['main-new', 'mine-2', 'mine-3']))
})

test('selection advances an edited checklist and preserves a custom selection', () => {
  const saved = [personal, main, mainOld]
  assert.equal(currentChecklistId(saved, 'main', 'main-old'), 'main-new')
  assert.equal(currentChecklistId(saved, 'main', 'mine'), 'mine')
  assert.equal(currentChecklistId(saved, 'main', 'missing'), 'main-new')
})

test('hidden selection falls back safely and never selects a test-only record', () => {
  const fixture = row('test', 'delivery-unseen-handoff', 'Test', '2026-11-08T10:00:00Z')
  assert.equal(currentChecklistId([fixture, main], 'main', 'test'), 'main-new')
  assert.equal(currentChecklistId([fixture], 'main', 'test'), '')
})

test('API newest-first order remains usable when fixtures omit timestamps', () => {
  const newer = {...personal, id: 'mine-latest', created_at: undefined}
  assert.equal(visibleChecklists([newer, {...personal, created_at: undefined}], 'main')[0].id, 'mine-latest')
})

test('configured main version stays selected while personal copies remain available', () => {
  const laterImport = row('later-main', 'main', 'Older imported rules', '2026-11-09T10:00:00Z', 'reviewed-015')
  const saved = [laterImport, personal, main, mainOld]
  assert.deepEqual(visibleChecklists(saved, 'main', 'reviewed-016').map(c => c.id), ['main-new', 'mine'])
  assert.equal(currentChecklistId(saved, 'main', '', 'reviewed-016'), 'main-new')
  assert.equal(currentChecklistId(saved, 'main', 'mine', 'reviewed-016'), 'mine')
})
