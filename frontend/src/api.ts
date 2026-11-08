import {ApiError, apiError} from './errorMessages.ts'
export {ApiError} from './errorMessages.ts'

export async function api<T>(path: string, body?: unknown): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, body === undefined ? undefined : {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body),
    })
  } catch {
    throw new ApiError('Не удалось связаться с сервером. Убедитесь, что приложение запущено, и проверьте подключение.', 'Сетевой запрос не получил ответа.')
  }
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw apiError(error?.detail, response.status)
  }
  try {return await response.json()}
  catch {throw new ApiError('Сервер вернул ответ в неподдерживаемом формате. Обновите страницу и попробуйте снова.', `Код ответа сервера: HTTP ${response.status}.`, response.status)}
}
