import test from 'node:test'
import assert from 'node:assert/strict'
import {failureAdvice, failureTitle} from '../src/assessmentFailure.ts'

test('provider credit exhaustion gives a top-up action instead of the HTTP 429 wait action', () => {
  assert.match(failureTitle('api_http_429', 'credit_balance_exhausted'), /Недостаточно средств/)
  assert.match(failureAdvice('api_http_429', 'credit_balance_exhausted'), /Пополните баланс у поставщика API/)
  assert.match(failureAdvice('api_http_429', 'credit_balance_exhausted'), /лимита расходов приложения не пополняет/)
  assert.equal(failureAdvice('provider_credit_exhausted_no_request'), failureAdvice('api_http_429', 'credit_balance_exhausted'))
  assert.match(failureAdvice('api_http_429', 'insufficient_quota'), /баланс и лимиты аккаунта у поставщика API/)
})

test('rate limits and an unqualified 429 advise waiting without claiming exhausted balance', () => {
  for (const providerCode of [undefined, null, 'rate_limit_exceeded']) {
    assert.match(failureTitle('api_http_429', providerCode), /частоту запросов/)
    assert.match(failureAdvice('api_http_429', providerCode), /Подождите/)
    assert.doesNotMatch(failureAdvice('api_http_429', providerCode), /Пополните|баланс/)
  }
})

test('key permissions and application budgets have distinct recovery actions', () => {
  assert.match(failureAdvice('api_http_401'), /Проверьте API-ключ/)
  assert.match(failureAdvice('api_http_403'), /разрешения API-ключа/)
  assert.match(failureAdvice('grading_budget_limit'), /общий лимит приложения/)
  assert.doesNotMatch(failureAdvice('grading_budget_limit'), /Пополните|поставщика/)
})

test('unknown provider codes never enter visible text or imitate an allowed quota code', () => {
  for (const providerCode of ['PRIVATE-CUSTOMER-TEXT', 'credit_balance_exhausted PRIVATE-CUSTOMER-TEXT',
    'prefix_insufficient_quota', '__proto__', 'toString']) {
    assert.equal(failureTitle('api_http_429', providerCode), failureTitle('api_http_429'))
    assert.equal(failureAdvice('api_http_429', providerCode), failureAdvice('api_http_429'))
    assert.equal(failureAdvice('PRIVATE-CUSTOMER-TEXT', providerCode), failureAdvice('unknown'))
    assert.doesNotMatch(failureTitle('PRIVATE-CUSTOMER-TEXT', providerCode) + failureAdvice('PRIVATE-CUSTOMER-TEXT', providerCode), /PRIVATE-CUSTOMER-TEXT/)
  }
})

test('validation, connection and interrupted results retain their guidance', () => {
  assert.match(failureTitle('invalid_evaluation_ValueError'), /не прошёл проверку/)
  assert.match(failureAdvice('api_connection_or_timeout'), /Проверьте подключение/)
  assert.match(failureAdvice('interrupted_by_restart'), /Сервис остановился/)
})
