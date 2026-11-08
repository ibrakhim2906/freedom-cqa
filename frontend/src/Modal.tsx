import {useEffect, useId, useRef, type ReactNode} from 'react'
import styles from './App.module.css'
import {Icon} from './Icon'

export function Modal({title, onClose, children, wide = false}: {title: string; onClose: () => void; children: ReactNode; wide?: boolean}) {
  const id = useId(), dialog = useRef<HTMLElement>(null), close = useRef(onClose)
  useEffect(() => {close.current = onClose}, [onClose])
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    dialog.current?.focus()
    const keys = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {event.preventDefault(); close.current(); return}
      if (event.key !== 'Tab') return
      const elements = [...(dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), summary, [tabindex="0"]') || [])]
        .filter(element => element.getClientRects().length > 0)
      const first = elements[0], last = elements.at(-1)
      if (!first) {event.preventDefault(); return}
      if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog.current)) {event.preventDefault(); last?.focus()}
      else if (!event.shiftKey && (document.activeElement === last || document.activeElement === dialog.current)) {event.preventDefault(); first.focus()}
    }
    document.addEventListener('keydown', keys)
    return () => {document.removeEventListener('keydown', keys); document.body.style.overflow = overflow; previous?.focus()}
  }, [])
  return <div className={styles.overlay} onClick={event => {if (event.target === event.currentTarget) onClose()}}>
    <section ref={dialog} role="dialog" aria-modal="true" aria-labelledby={id} tabIndex={-1} className={`${styles.dialog} ${styles.setupDialog} ${wide ? styles.wideDialog : ''}`}>
      <div className={styles.dialogHeading}><h2 id={id}>{title}</h2><button aria-label="Закрыть окно" onClick={onClose}><Icon name="close"/></button></div>
      {children}
    </section>
  </div>
}
