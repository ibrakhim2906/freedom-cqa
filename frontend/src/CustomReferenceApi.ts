import type {ConversationDetail, EvidenceContext, Reference} from './types'

export type CustomReferenceDraft = {title: string; text: string; source_url: string; source_note: string; scope: string;
  date_kind: 'unknown'|'snapshot'|'validity'; snapshot_on: string; valid_from: string; valid_until: string}
export type CustomReferenceSummary = {added: number; reused: number; context: EvidenceContext;
  documents: {id: string; title: string; warnings: string[]; usable: boolean; rejection_reasons: string[]}[]}
export type CustomReferenceMetadata = Pick<CustomReferenceDraft, 'title'|'date_kind'> & {
  source_url: string|null; source_note: string|null; scope: string|null; snapshot_on: string|null;
  valid_from: string|null; valid_until: string|null; origin: 'user_provided'}
export type CustomReferenceSaved = ConversationDetail & {custom_reference_summary: CustomReferenceSummary}

export function customReferenceMetadata(source: ConversationDetail): Record<string, CustomReferenceMetadata> {
  const metadata = source.metadata as typeof source.metadata & {custom_reference_documents?: Record<string, CustomReferenceMetadata>}
  return metadata.custom_reference_documents && typeof metadata.custom_reference_documents === 'object'
    && !Array.isArray(metadata.custom_reference_documents) ? metadata.custom_reference_documents : {}
}

export function referenceTitle(reference: Pick<Reference, 'id'>, metadata?: ConversationDetail['metadata']) {
  const documents = (metadata as {custom_reference_documents?: Record<string, {title?: unknown}>} | undefined)?.custom_reference_documents
  const title = documents?.[reference.id]?.title
  return typeof title === 'string' && title.trim() ? title
    : reference.id === 'example-address-help' ? 'Как изменить адрес — учебная справка' : reference.id
}

export const customReferenceWarning = (code: string) => ({
  user_provided: 'Документ предоставлен пользователем. Приложение не проверяет его подлинность и официальный статус.',
  source_unknown: 'Источник не указан.', scope_unknown: 'Тема или продукт не указаны: соответствие диалогу не подтверждено.',
  date_unknown: 'Дата актуальности не указана: действие документа на дату диалога не подтверждено.',
} as Record<string, string>)[code] || 'Применимость документа требует уточнения.'

function errorMessage(detail: unknown) {
  const value = detail && typeof detail === 'object' ? detail as {code?: string; field?: string; document_index?: number} : {}
  const messages: Record<string, string> = {
    empty_field: 'Название и текст документа не должны быть пустыми.',
    invalid_url: 'Укажите ссылку, начинающуюся с http:// или https://, без логина и пароля.',
    invalid_date: 'Укажите существующую дату в формате ГГГГ-ММ-ДД.',
    inconsistent_dates: 'Выберите, что известно о дате документа, или очистите поля дат.',
    snapshot_date_required: 'Укажите дату сохранения сведений. Для такого документа период действия не задаётся.',
    validity_dates_required: 'Укажите хотя бы начало или окончание периода действия.',
    reversed_dates: 'Начало действия документа не может быть позже окончания.',
    total_text_limit: 'За один раз можно прикрепить не более 300 000 символов текста. Разделите документы на несколько загрузок.',
    request_too_large: 'Документы слишком большие. Разделите текст на несколько загрузок.',
    document_count_limit: 'К диалогу уже прикреплено слишком много пользовательских документов. Допускается до 100.',
    reference_conflict: 'Такой идентификатор источника уже занят другим содержимым. Обновите диалог и повторите действие.',
    conversation_not_found: 'Диалог не найден. Обновите страницу и выберите его снова.',
    invalid_json: 'Не удалось прочитать запрос. Обновите страницу и повторите действие.',
  }
  const fields: Record<string, string> = {title: 'Название должно содержать от 1 до 200 символов.',
    text: 'Текст должен содержать от 1 до 100 000 символов.', documents: 'Можно прикрепить от 1 до 10 документов за один раз.',
    source_url: 'Проверьте ссылку на источник.', source_note: 'Описание источника — не более 1000 символов.',
    scope: 'Название продукта или темы — не более 200 символов.', date_kind: 'Выберите один из предложенных вариантов даты.'}
  const known = value.code && Object.hasOwn(messages, value.code) ? messages[value.code]
    : value.code === 'invalid_field' && value.field && Object.hasOwn(fields, value.field) ? fields[value.field]
      : 'Не удалось прикрепить документы. Проверьте заполненные поля и повторите действие.'
  const index = value.document_index
  return typeof index === 'number' && Number.isInteger(index) && index >= 1 && index <= 10 ? `Документ ${index}: ${known}` : known
}

export async function customReferenceRequest<T>(conversationId: string, documents: CustomReferenceDraft[], preview = false): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api/conversations/${encodeURIComponent(conversationId)}/custom-references${preview ? '/preview' : ''}`, {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({documents}),
    })
  } catch {throw new Error('Не удалось связаться с сервером. Проверьте, что приложение запущено, и повторите действие.')}
  const value = await response.json().catch(() => null)
  if (!response.ok) throw new Error(errorMessage(value?.detail))
  if (!value) throw new Error('Сервер вернул неожиданный ответ. Обновите страницу и проверьте сохранённые документы.')
  return value as T
}
