export class ApiError extends Error {
  readonly technicalDetails?: string
  readonly status?: number
  constructor(message: string, technicalDetails?: string, status?: number) {
    super(message)
    this.name = 'ApiError'
    this.technicalDetails = technicalDetails
    this.status = status
  }
}

const lookup = (values: Record<string, string>, key: string) => Object.hasOwn(values, key) ? values[key] : undefined

const fixedMessages: Record<string, string> = {
  'Organizer response reports failure; no source records were accepted': 'Источник сообщает об ошибке. Диалоги не загружены; получите успешный ответ с данными.',
  'Import between 1 and 1000 conversations': 'В одном файле должно быть от 1 до 1000 диалогов.',
  'data: expected an object containing records (an array of conversations)': 'В поле data нужен объект с массивом диалогов records. Сверьте структуру с примером файла.',
  'Set OPENAI_API_KEY locally in .env; there is no offline evaluation fallback': 'Для проверки нужен API-ключ. Укажите OPENAI_API_KEY в файле .env на сервере и перезапустите приложение. Инструкция есть в разделе «Настройка и помощь».',
  'Batch budget exceeds the configured lifetime limit': 'Лимит выбранных диалогов превышает общий лимит приложения. Уменьшите сумму или измените общий лимит в настройках сервера.',
  'Budget allowance exceeded': 'Достигнут лимит расходов. Проверьте доступный остаток в разделе «Настройка и помощь».',
  'Insufficient remaining budget for the first attempt and bounded repair allowance': 'Оставшегося лимита недостаточно для проверки и предусмотренной попытки исправления ответа. Проверьте общий лимит расходов.',
  'Batch budget cannot cover the first attempt and bounded repair allowance': 'Лимита выбранных диалогов недостаточно для проверки и предусмотренной попытки исправления ответа. Увеличьте лимит или выберите меньше диалогов.',
  'Request exceeds its protected repair allowance': 'Для исправления ответа недостаточно выделенного лимита. Проверьте настройки расходов перед новым запуском.',
  'A budget group requires a positive finite limit': 'Укажите положительный лимит расходов.',
  'Reservation must be positive and finite': 'Укажите корректный положительный лимит расходов.',
  'Request ID was already used for different inputs': 'Этот запрос уже использован для других данных. Обновите страницу и повторите действие.',
  'Selected checklist version does not exist': 'Выбранная версия чек-листа не найдена. Обновите список и выберите чек-лист снова.',
  'Selected conversation revision does not exist': 'Выбранная версия диалога не найдена. Обновите список и выберите диалог снова.',
  'Record not found': 'Запись не найдена. Обновите страницу.',
  'Conversation not found': 'Диалог не найден. Обновите список диалогов.',
  'Reference pack not found': 'Набор источников не найден. Обновите список и выберите его снова.',
  'Checklist ID, version and title cannot be blank': 'Заполните название, идентификатор и версию чек-листа.',
  'Each criterion needs an ID, title and a substantive instruction': 'У каждого критерия должны быть название, идентификатор и понятное правило оценки.',
  'Every answer level needs a value and a description': 'У каждого варианта ответа должны быть значение и описание.',
  'That checklist ID/version already exists with different content. Save a new version.': 'Чек-лист с таким идентификатором и версией уже существует. Сохраните изменения как новую версию.',
  'Criterion needs nonempty, unique allowed levels': 'Добавьте хотя бы один вариант ответа. Значения вариантов не должны повторяться.',
  'A flag must have zero scoring weight': 'У отдельной отметки вес должен быть равен 0: она не влияет на итоговую оценку.',
  'Checklist needs nonempty, unique criteria': 'Добавьте хотя бы один критерий. Идентификаторы критериев не должны повторяться.',
  'This evaluation is still active': 'Эта проверка ещё выполняется. Дождитесь её завершения.',
  'Only queued evaluations can be cancelled; active requests may already be billable': 'Отменить можно только проверку в очереди. Уже отправленный запрос может быть платным.',
  'Only a completed evaluation can be appealed': 'Запросить пересмотр можно после завершения проверки.',
  'Appeal must reference a configured criterion and actual messages': 'Выберите критерий из чек-листа и сообщения из этого диалога.',
  'Appeal author and rationale cannot be blank': 'Укажите автора запроса и причину пересмотра.',
  'Proposed answer is not an allowed criterion level': 'Выберите один из вариантов ответа, заданных для этого критерия.',
  'Answer is not an allowed criterion level': 'Выберите один из вариантов ответа, заданных для этого критерия.',
  'A proposed answer requires a proposed status': 'Для предложенного ответа укажите статус решения.',
  'Unscored proposals must have a null answer': 'Для решения без оценки не выбирайте вариант ответа.',
  'N/A and needs-review answers must be null': 'Для статусов «Не применяется» и «Нужно решение» не выбирайте вариант ответа.',
  'N/A is forbidden for this criterion': 'Для этого критерия не предусмотрен вариант «Не применяется».',
  'This criterion already has an open appeal': 'По этому критерию уже есть запрос на пересмотр. Сначала рассмотрите его.',
  'Reviewer and decision rationale cannot be blank': 'Укажите проверяющего и причину решения.',
  'Review changed. Reload the current evaluation before resolving.': 'Результат уже изменён. Обновите страницу перед сохранением решения.',
  'Another review was saved. Reload before resolving.': 'Уже сохранено другое решение. Обновите страницу перед продолжением.',
  'Accepting an appeal requires a full replacement judgment for that criterion': 'Для принятия пересмотра заполните новое решение по критерию целиком.',
  'Review references must have unique IDs': 'У источников пересмотра должны быть разные идентификаторы.',
  'A review source cannot replace a frozen reference with different content': 'Нельзя заменить сохранённый источник другим содержимым. Добавьте новый источник с другим идентификатором.',
  "A review reference does not match the original conversation's scope/date": 'Источник не подходит по теме или дате исходного диалога. Проверьте его область применения.',
  'A rejected appeal cannot replace the judgment': 'При отклонении запроса исходное решение не меняется.',
  'Additional review sources require an accepted decision': 'Добавить источники можно при принятии пересмотра.',
  'Every criterion requires a substantive explanation': 'Добавьте обоснование для каждого критерия.',
  'Needs-review judgments must identify the uncertainty': 'Укажите, какие сведения нужно уточнить для решения по критерию.',
  'Judgment needs source evidence or a checked omission span': 'Выберите подтверждающую цитату или участок диалога, где проверялось отсутствие нужного действия.',
  'Evidence quote must occur verbatim in the referenced original message': 'Цитата должна точно совпадать с исходным сообщением. Выберите текст заново, без изменений.',
  'Reference quote must occur verbatim in the supplied reference': 'Цитата должна точно совпадать с текстом источника. Выберите её заново, без изменений.',
  'Checked span references a nonexistent message': 'Одно из выбранных сообщений не найдено в диалоге. Выберите сообщения заново.',
  'Both evaluations need a saved effective result before comparison': 'Для сравнения нужны два завершённых результата.',
  'Model has no configured cost rates; add verified rates before use': 'Для выбранной модели не настроен расчёт стоимости. Проверьте настройки сервера.',
}

const fieldNames: Record<string, string> = {
  record: 'запись', conversation: 'диалог', id: 'идентификатор', conversation_id: 'идентификатор диалога',
  channel: 'канал', language: 'язык', messages: 'сообщения', transcript: 'сообщения', timestamp: 'время сообщения',
  speaker: 'отправитель', text: 'текст', references: 'источники', provenance: 'происхождение источника', source_url: 'ссылка на источник',
  retrieved_on: 'дата получения', scope: 'область применения', valid_from: 'начало действия', valid_until: 'окончание действия',
  date_basis: 'основание даты', snapshot_on: 'дата сведений', knowledge_scope: 'тема диалога', occurred_on: 'дата диалога',
  occurred_on_origin: 'источник даты диалога', reference_context: 'контекст источников', mode: 'режим', as_of: 'дата проверки',
  rationale: 'причина решения', pack_id: 'идентификатор набора', pack_sha256: 'контрольная сумма набора',
  'unrecognized field': 'лишнее поле', title: 'название', version: 'версия', instructions: 'общие инструкции', criteria: 'критерии',
  instruction: 'правило оценки', kind: 'тип критерия', weight: 'вес критерия', na_condition: 'условие неприменимости',
  channel_guidance: 'указания для канала', levels: 'варианты ответа', value: 'значение', fraction: 'доля баллов', description: 'описание',
  budget_usd: 'лимит расходов', conversation_ids: 'выбранные диалоги', checklist_id: 'чек-лист', request_id: 'идентификатор запроса',
  strategy: 'режим проверки', force: 'повторная проверка', content: 'содержимое файла', criterion_id: 'критерий',
  author: 'автор', reason: 'причина запроса', message_ids: 'выбранные сообщения', proposed: 'предложенное решение',
  reviewer: 'проверяющий', decision: 'решение', expected_revision: 'версия результата', judgment: 'результат по критерию',
  status: 'статус', answer: 'ответ', explanation: 'обоснование', evidence: 'цитаты', counterevidence: 'противоречащие цитаты',
  checked_message_ids: 'проверенные сообщения', uncertainty: 'непроверенные сведения', quote: 'цитата', message_id: 'сообщение',
}

const importGuidance: Record<string, string> = {
  'use "agent chat" or "voice call"': 'укажите канал: "agent chat" для чата или "voice call" для звонка',
  'use "client", "operator", "bot", or "system"': 'укажите отправителя: "client", "operator", "bot" или "system"',
  'use a text timestamp, for example "00:01" or an ISO date-time': 'укажите время текстом, например "00:01", или дату и время в формате ISO',
  'use text for the language, for example "EN", "RU", or "KZ"': 'укажите язык текстом, например "EN", "RU" или "KZ"',
  'use a text identifier': 'укажите идентификатор текстом',
  'use a nonempty text identifier': 'укажите непустой текстовый идентификатор',
  'use text for the message or reference': 'укажите текст сообщения или источника',
  'use an array of message objects': 'поместите сообщения в массив объектов',
  'expected an array of message objects': 'поместите сообщения в массив объектов',
  'use an array of reference objects': 'поместите источники в массив объектов',
  'use "supplied" or "source_iso_timestamps"': 'укажите "supplied" или "source_iso_timestamps"',
  'use "policy_validity" or "snapshot"': 'укажите "policy_validity" или "snapshot"',
  'use "conversation_date" or "snapshot_review"': 'укажите "conversation_date" или "snapshot_review"',
  'use a 64-character lowercase hexadecimal hash': 'укажите контрольную сумму из 64 символов: цифр и строчных букв от a до f',
  'provide this field': 'заполните обязательное поле',
  'remove this extra property; use only the fields in the example dataset': 'удалите лишнее поле; используйте структуру из примера файла',
  'expected text': 'ожидается текст',
  'expected an array': 'ожидается массив',
  'expected an object with the required fields': 'ожидается объект с обязательными полями',
  'expected a conversation object': 'ожидается объект с данными диалога',
  'expected an object with conversation fields': 'ожидается объект с данными диалога',
  'expected a message object': 'ожидается объект с полями сообщения',
  'include at least one message': 'добавьте хотя бы одно сообщение',
  'use a unique ID within this conversation': 'укажите уникальный идентификатор: он не должен повторяться в этом диалоге',
  'use a valid calendar date in YYYY-MM-DD format': 'укажите существующую дату в формате ГГГГ-ММ-ДД',
  'use valid YYYY-MM-DD dates; validity must start before it ends; snapshot references need snapshot_on and no validity interval': 'укажите даты в формате ГГГГ-ММ-ДД. Начало действия не должно быть позже окончания. Для снимка источника нужны snapshot_on и отсутствие интервала действия',
  'provide scope, rationale and pack_id; snapshot_review needs a YYYY-MM-DD as_of date, while conversation_date must not set as_of': 'заполните scope, rationale и pack_id. Для snapshot_review нужна дата as_of в формате ГГГГ-ММ-ДД; для conversation_date поле as_of должно быть пустым',
  'check this field against the example dataset': 'сверьте это поле с примером файла',
  'use at most 10000 messages per conversation': 'в одном диалоге допускается не более 10000 сообщений',
  'use nonempty text': 'введите текст; поле не должно быть пустым или состоять из пробелов',
}

function describePath(path: string) {
  const parts = path.split('.').map(part => /^([a-z_]+|unrecognized field)(?:\[(\d{1,6})\])?$/.exec(part))
  if (parts.some(part => !part || !Object.hasOwn(fieldNames, part[1]))) return null
  return parts.map(part => {
    const [, name, index] = part!
    const labels: Record<string, string> = {messages: 'сообщение', transcript: 'сообщение', references: 'источник', criteria: 'критерий', levels: 'вариант ответа'}
    return index ? `${labels[name] || fieldNames[name]} ${index}` : fieldNames[name]
  }).join(', ')
}

function importMessage(detail: string) {
  const syntax = /^(JSONL?) line (\d+), column (\d+): invalid syntax\. Use valid JSON, or one complete JSON object per JSONL line; check quotes, commas and brackets\.$/.exec(detail)
  if (syntax) return `${syntax[1]}, строка ${syntax[2]}, позиция ${syntax[3]}: ошибка формата. Проверьте кавычки, запятые и скобки. В JSONL каждый объект должен целиком помещаться в одной строке.`
  const generic = /^Record (\d+): check the conversation fields against the example dataset$/.exec(detail)
  if (generic) return `Диалог ${generic[1]}: сверьте поля с примером файла.`
  const record = /^Record (\d+), ([^:]+): (.+)$/.exec(detail)
  if (!record) return null
  const [, index, path, originalReason] = record
  const reason = originalReason.replace(/^required; /, '')
  const guidance = lookup(importGuidance, reason)
  const location = describePath(path)
  if (!guidance || !location) return null
  // These instructions name the field themselves, so don't repeat it in the location.
  const namesField = /^(?:use "agent chat"|use "client"|use a text timestamp|use text for the language|use a (?:nonempty )?text identifier|use text for the message)/.test(reason)
  const parent = namesField ? describePath(path.split('.').slice(0, -1).join('.')) : location
  return `Диалог ${index}${parent ? `, ${parent}` : ''}: ${guidance}.`
}

function validationMessage(detail: unknown[]) {
  const issue = detail[0]
  if (!issue || typeof issue !== 'object') return null
  const {loc, type, msg} = issue as {loc?: unknown[]; type?: string; msg?: string}
  const path = Array.isArray(loc) ? loc.filter(part => part !== 'body').map((part, index) => {
    if (typeof part === 'number' && Number.isInteger(part) && part >= 0) return `[${part + 1}]`
    return typeof part === 'string' ? `${index > 0 ? '.' : ''}${part}` : ''
  }).join('') : ''
  const location = describePath(path)
  const known = typeof msg === 'string' ? lookup(fixedMessages, msg.replace(/^Value error, /, '')) : undefined
  if (known) return location ? `${location[0].toUpperCase()}${location.slice(1)}: ${known}` : known
  const guidance: Record<string, string> = {
    missing: 'заполните обязательное поле', string_type: 'укажите текст', string_too_short: 'значение слишком короткое',
    string_too_long: 'значение слишком длинное', list_type: 'ожидается массив', model_type: 'ожидается объект с обязательными полями',
    int_parsing: 'укажите целое число', int_type: 'укажите целое число', float_parsing: 'укажите число', float_type: 'укажите число',
    greater_than: 'число должно быть больше допустимого минимума', greater_than_equal: 'число меньше допустимого минимума',
    less_than: 'число должно быть меньше допустимого максимума', less_than_equal: 'число превышает допустимый максимум',
    literal_error: 'выберите один из допустимых вариантов', extra_forbidden: 'удалите лишнее поле',
    too_short: 'добавьте хотя бы один элемент', too_long: 'сократите число элементов',
  }
  const reason = type ? lookup(guidance, type) : undefined
  return location && reason ? `${location[0].toUpperCase()}${location.slice(1)}: ${reason}.` : null
}

export function apiError(detail: unknown, status: number) {
  const known = typeof detail === 'string' ? lookup(fixedMessages, detail) || importMessage(detail)
    : Array.isArray(detail) ? validationMessage(detail) : null
  const fallback: Record<number, string> = {
    401: 'Не удалось выполнить запрос: нужна авторизация. Проверьте настройки сервиса.',
    403: 'Нет доступа к этому действию. Проверьте настройки сервиса.',
    404: 'Запись не найдена. Обновите страницу.',
    409: 'Данные изменились. Обновите страницу и повторите действие.',
    413: 'Файл слишком большой. Разделите данные на несколько файлов и загрузите их по очереди.',
    422: 'Не удалось обработать данные. Проверьте формат и обязательные поля.',
    429: 'Сервис временно ограничил запросы. Подождите немного и повторите действие.',
  }
  // Arbitrary backend messages and validation input/context may contain customer
  // text. Keep only the HTTP status for unknown failures, never log the payload.
  return new ApiError(known || fallback[status] || 'Не удалось выполнить запрос. Проверьте работу сервера и повторите действие.', `Код ответа сервера: HTTP ${status}.`, status)
}
