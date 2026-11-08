import test from 'node:test'
import assert from 'node:assert/strict'
import {parseTranscript} from '../src/transcriptImport.ts'

test('Russian roles preserve message text and do not invent timestamps', () => {
  assert.deepEqual(parseTranscript('Клиент: Где отчёт?\nОператор: Откройте «Отчёты».\nВторая строка ответа.'), [
    {id:'m1', speaker:'client', timestamp:'', text:'Где отчёт?'},
    {id:'m2', speaker:'operator', timestamp:'', text:'Откройте «Отчёты».\nВторая строка ответа.'},
  ])
})
test('timestamps, system events and bot replies retain their own roles', () => {
  const rows = parseTranscript('[00:12] Клиент: Помогите\r\nБот: Соединяю\r\nСистема: Оператор подключён\r\n[00:01:02] Оператор: Здравствуйте')
  assert.deepEqual(rows.map(m => [m.timestamp, m.speaker]), [['00:12','client'],['','bot'],['','system'],['00:01:02','operator']])
})
test('unlabelled, unknown-role and empty messages require correction', () => {
  assert.throws(() => parseTranscript('Просто текст'), /Клиент/)
  assert.throws(() => parseTranscript('Клиент: Привет\nПосетитель: Ответ'), /отправителя/)
  assert.throws(() => parseTranscript('Клиент:\nОператор: Привет'), /Реплика 1 пустая/)
})
test('English role markers keep non-Russian source wording unchanged', () => {
  assert.equal(parseTranscript('Client: Where is it?\nAgent: Open Reports.')[1].text, 'Open Reports.')
})

test('ordinary colon-prefixed continuation lines remain part of the original message', () => {
  const text = 'Нужна помощь.\nНомер заказа:123\nВажно: не меняйте дату.\nСсылка: https://example.com/a\nhttps://example.com/b\n\nАдрес доставки: Алматы'
  assert.deepEqual(parseTranscript(`Клиент: ${text}\n[00:15] Оператор: Проверю.`), [
    {id: 'm1', speaker: 'client', timestamp: '', text},
    {id: 'm2', speaker: 'operator', timestamp: '00:15', text: 'Проверю.'},
  ])
})

test('likely misspelled roles and timestamped unknown senders require correction instead of merging', () => {
  for (const label of ['Клент', 'Оператр', 'Опертатор', 'Клинет', 'Clientt', 'Агент', '[00:15] Иван', '[bad] Оператор']) {
    assert.throws(() => parseTranscript(`Клиент: Привет\n${label}: Ответ`), /отправителя/, label)
  }
})

test('a labelled empty reply is still invalid even after valid multiline content', () => {
  assert.throws(() => parseTranscript('Клиент: Помогите\nНомер заказа: 123\nОператор: '), /Реплика 2 пустая/)
})
