// Provider metadata is matched against known codes and is never displayed verbatim.
function failureContent(code: string, providerCode?: string|null): [string, string] {
  if (code.includes('budget')) return ['Достигнут лимит расходов на проверку',
    'Проверьте лимит выбранных диалогов и общий лимит приложения. Оценка не была выставлена.']
  if (providerCode === 'credit_balance_exhausted' || code === 'provider_credit_exhausted_no_request') return [
    'Недостаточно средств на счёте поставщика API',
    'Пополните баланс у поставщика API, затем повторите проверку. Увеличение лимита расходов приложения не пополняет этот счёт.']
  if (providerCode === 'insufficient_quota') return ['Исчерпан баланс или лимит аккаунта поставщика API',
    'Проверьте баланс и лимиты аккаунта у поставщика API. При необходимости пополните счёт или увеличьте лимит, затем повторите проверку.']
  if (code === 'api_http_401') return ['API-ключ не принят сервисом',
    'Проверьте API-ключ в настройках сервера. После исправления ключа повторите проверку.']
  if (code === 'api_http_403') return ['Нет доступа к сервису проверки',
    'Проверьте разрешения API-ключа и доступ аккаунта к выбранной модели, затем повторите проверку.']
  if (providerCode === 'rate_limit_exceeded' || code === 'api_http_429') return [
    'Сервис временно ограничил частоту запросов',
    'Подождите немного и повторите проверку. Если ограничение повторяется, уменьшите частоту запросов.']
  if (code.includes('invalid_evaluation') || code.includes('validation')) return ['Результат не прошёл проверку',
    'Ответ не соответствует требованиям к результату или доказательствам. Прочитайте сведения об ошибке и при необходимости запустите проверку повторно.']
  if (code.includes('connection') || code.includes('timeout')) return ['Сервис проверки не ответил',
    'Проверьте подключение и доступность сервиса. Повторная попытка может потребовать оплаты.']
  if (code.includes('restart') || code.includes('interrupted')) return ['Проверка прервана',
    'Сервис остановился до завершения проверки. Прочитайте сведения о сбое перед новой платной попыткой.']
  return ['Проверка не завершена', 'Эта попытка не дала оценки. Прочитайте сведения об ошибке перед повторным запуском.']
}

export function failureTitle(code: string, providerCode?: string|null) {
  return failureContent(code, providerCode)[0]
}

export function failureAdvice(code: string, providerCode?: string|null) {
  return failureContent(code, providerCode)[1]
}
