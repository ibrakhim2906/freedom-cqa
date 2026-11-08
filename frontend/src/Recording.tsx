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
    <a href={source} target="_blank" rel="noreferrer"><Icon name="call" size={14}/>Open original recording<Icon name="arrow" size={13}/></a>
    {direct && !unavailable && <audio controls preload="none" src={source} onError={() => setUnavailable(true)} aria-label="Original call recording"/>}
    {unavailable && <p>Playback is unavailable here. Open the original recording to listen.</p>}
    <p>Assessment uses the transcript. Voice quality has not been analyzed.</p>
  </div>
}
