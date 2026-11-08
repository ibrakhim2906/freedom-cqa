import test from 'node:test'
import assert from 'node:assert/strict'
import {ApiError, apiError} from '../src/errorMessages.ts'
import {api} from '../src/api.ts'

const privateText = 'PRIVATE-CUSTOMER-TEXT'

test('failed source envelopes have a precise Russian explanation', () => {
  assert.equal(apiError('Organizer response reports failure; no source records were accepted', 422).message,
    'Источник сообщает об ошибке. Диалоги не загружены; получите успешный ответ с данными.')
})

test('organizer message errors give Russian guidance while preserving supported role values', () => {
  const error = apiError('Record 1, transcript[2].speaker: required; use "client", "operator", "bot", or "system"', 422)
  assert.ok(error instanceof ApiError)
  assert.equal(error.message, 'Диалог 1, сообщение 2: укажите отправителя: "client", "operator", "bot" или "system".')
  assert.equal(error.status, 422)
})

test('nested canonical fields and duplicate IDs retain record/message positions', () => {
  assert.equal(apiError('Record 2, messages[3].id: use a unique ID within this conversation', 422).message,
    'Диалог 2, сообщение 3, идентификатор: укажите уникальный идентификатор: он не должен повторяться в этом диалоге.')
  assert.match(apiError('Record 2, references[1].valid_from: expected text', 422).message, /^Диалог 2, источник 1, начало действия: ожидается текст/)
  assert.equal(apiError('Record 1, conversation_id: required; use a text identifier', 422).message,
    'Диалог 1: укажите идентификатор текстом.')
})

test('syntax errors preserve JSONL line numbers and actionable punctuation guidance', () => {
  const error = apiError('JSONL line 7, column 22: invalid syntax. Use valid JSON, or one complete JSON object per JSONL line; check quotes, commas and brackets.', 422)
  assert.match(error.message, /JSONL, строка 7, позиция 22/)
  assert.match(error.message, /кавычки, запятые и скобки/)
})

test('request-validation guidance strips raw values, unknown keys, and exception context', () => {
  const error = apiError([{loc: ['body', 'criteria', 0, 'levels', 1, 'fraction'], type: 'less_than_equal',
    msg: privateText, input: privateText, ctx: {error: privateText}}], 422)
  assert.equal(error.message, 'Критерий 1, вариант ответа 2, доля баллов: число превышает допустимый максимум.')
  assert.ok(!JSON.stringify(error).includes(privateText))
  const unknown = apiError([{loc: ['body', privateText], msg: privateText, type: 'value_error', input: privateText}], 422)
  assert.equal(unknown.message, 'Не удалось обработать данные. Проверьте формат и обязательные поля.')
  assert.ok(!JSON.stringify(unknown).includes(privateText))
})

test('unknown backend messages cannot leak customer data through primary or technical text', () => {
  for (const detail of [privateText, `Record 1, messages[1].${privateText}: expected text`,
    `Record 1, messages[1].text: ${privateText}`, {detail: privateText}, 'toString', '__proto__']) {
    const error = apiError(detail, 500)
    assert.equal(error.message, 'Не удалось выполнить запрос. Проверьте работу сервера и повторите действие.')
    assert.equal(error.technicalDetails, 'Код ответа сервера: HTTP 500.')
    assert.ok(!error.message.includes(privateText))
  }
})

test('key and spending failures lead to useful setup actions', () => {
  assert.match(apiError('Set OPENAI_API_KEY locally in .env; there is no offline evaluation fallback', 422).message, /Настройка и помощь/)
  assert.match(apiError('Batch budget exceeds the configured lifetime limit', 422).message, /Уменьшите сумму/)
  assert.match(apiError('That checklist ID/version already exists with different content. Save a new version.', 422).message, /новую версию/)
  assert.match(apiError('This criterion already has an open appeal', 409).message, /уже есть запрос на пересмотр/)
})

test('API network failures have Russian guidance and never echo the native error', async t => {
  t.mock.method(globalThis, 'fetch', async () => {throw new TypeError(privateText)})
  await assert.rejects(api('/conversations'), error => {
    assert.ok(error instanceof ApiError)
    assert.match(error.message, /Не удалось связаться с сервером/)
    assert.ok(!JSON.stringify(error).includes(privateText))
    return true
  })
})

test('API error responses localize safely and successful requests preserve payloads', async t => {
  const calls = []
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    calls.push({url, options})
    return new Response(JSON.stringify({detail: [{loc: ['body', 'criteria', 0, 'title'], type: 'missing', input: privateText}]}), {status: 422})
  })
  await assert.rejects(api('/checklists', {title: 'Мой чек-лист'}), error => {
    assert.equal(error.message, 'Критерий 1, название: заполните обязательное поле.')
    assert.ok(!JSON.stringify(error).includes(privateText))
    return true
  })
  assert.equal(calls[0].url, '/api/checklists')
  assert.equal(calls[0].options.method, 'POST')
  assert.deepEqual(JSON.parse(calls[0].options.body), {title: 'Мой чек-лист'})
  globalThis.fetch = async () => new Response(JSON.stringify({content: privateText}), {status: 200})
  assert.deepEqual(await api('/conversations/saved'), {content: privateText})
})
