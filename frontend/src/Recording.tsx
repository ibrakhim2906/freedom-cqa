import {useState} from 'react'
import {safeLink} from './format'
import {Icon} from './Icon'
import styles from './App.module.css'

export function Recording({url}: {url: string}) {
  const [unavailable, setUnavailable] = useState(false)
  const source = safeLink(url)
  if (!source) return null
  // Share/preview pages cannot serve as audio sources. Their original link stays available.
  const direct = /\.(mp3|wav|m4a|ogg|oga|aac|flac|webm)(?:[?#]|$)/i.test(source)
  return <div className={styles.recording}>
    <a href={source} target="_blank" rel="noreferrer"><Icon name="call" size={14}/>Открыть запись звонка<Icon name="arrow" size={13}/></a>
    {direct && !unavailable && <audio controls preload="none" src={source} onError={() => setUnavailable(true)} aria-label="Запись звонка"/>}
    {unavailable && <p>Встроенный плеер не может воспроизвести запись. Откройте её по ссылке.</p>}
    <p>Проверка выполнена по тексту диалога. Качество речи не оценивалось.</p>
  </div>
}
