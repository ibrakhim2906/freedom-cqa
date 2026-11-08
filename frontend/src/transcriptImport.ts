export type TranscriptMessage = {id: string; speaker: 'client'|'operator'|'bot'|'system'; timestamp: string; text: string}

const roles: Record<string, TranscriptMessage['speaker']> = {
  'клиент': 'client', 'оператор': 'operator', 'бот': 'bot', 'система': 'system',
  client: 'client', customer: 'client', operator: 'operator', agent: 'operator', bot: 'bot', system: 'system',
}

const otherSpeakerLabels = new Set(['посетитель', 'покупатель', 'сотрудник', 'менеджер', 'консультант', 'продавец', 'администратор', 'агент', 'support', 'user', 'assistant', 'visitor'])

function resemblesRole(label: string, role: string) {
  if (role.length < 5 || Math.abs(label.length - role.length) > 1) return false
  if (label.length === role.length) {
    const different = [...label].map((letter, i) => letter === role[i] ? -1 : i).filter(i => i >= 0)
    if (different.length <= 1) return true
    const [first, second] = different
    return different.length === 2 && second === first + 1 && label[first] === role[second] && label[second] === role[first]
  }
  const [shorter, longer] = label.length < role.length ? [label, role] : [role, label]
  let position = 0
  while (position < shorter.length && shorter[position] === longer[position]) position++
  return shorter.slice(position) === longer.slice(position + 1)
}

function likelySpeakerBoundary(line: string) {
  const prefix = line.match(/^\s*(\[[^\]]+\]\s*)?([\p{L}][\p{L} ]{0,30})\s*:/u)
  if (!prefix) return false
  const label = prefix[2].trim().toLocaleLowerCase('ru-RU')
  return !!prefix[1] || otherSpeakerLabels.has(label) || Object.keys(roles).some(role => label === role || resemblesRole(label, role))
}

export function parseTranscript(text: string): TranscriptMessage[] {
  const messages: TranscriptMessage[] = []
  for (const line of text.replaceAll('\r\n', '\n').split('\n')) {
    const match = line.match(/^\s*(?:\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*)?(Клиент|Оператор|Бот|Система|Client|Customer|Operator|Agent|Bot|System)\s*:\s*(.*)$/i)
    if (match) {
      messages.push({id: `m${messages.length + 1}`, timestamp: match[1] || '', speaker: roles[match[2].toLowerCase()], text: match[3]})
    } else if (line.trim()) {
      if (!messages.length) throw new Error('Начните первую реплику с «Клиент:» или «Оператор:». Каждая новая реплика должна начинаться с обозначения отправителя.')
      if (likelySpeakerBoundary(line)) {
        throw new Error('Не удалось определить отправителя одной из реплик. Используйте «Клиент:», «Оператор:», «Бот:» или «Система:». Время можно указать перед отправителем: [00:15] Клиент: …')
      }
      messages[messages.length - 1].text += '\n' + line
    } else if (messages.length) {
      messages[messages.length - 1].text += '\n'
    }
  }
  if (!messages.length) throw new Error('Добавьте хотя бы одну реплику.')
  if (messages.length > 10000) throw new Error('В одном диалоге может быть не более 10 000 сообщений.')
  messages.forEach((message, index) => {
    message.text = message.text.trim()
    if (!message.text) throw new Error(`Реплика ${index + 1} пустая. Добавьте текст или удалите обозначение отправителя.`)
  })
  return messages
}
