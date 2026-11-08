import type {CSSProperties} from 'react'

export function Icon({name, size = 18, style}: {name: 'search'|'upload'|'chat'|'call'|'check'|'arrow'|'list'|'history'|'settings'|'close'|'file'|'play'|'shield'; size?: number; style?: CSSProperties}) {
  const paths = {
    search: <><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4.5 4.5"/></>,
    upload: <><path d="M12 16V3m-5 5 5-5 5 5M4 15v5h16v-5"/></>,
    chat: <path d="M5 4h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-6 4V6a2 2 0 0 1 2-2Z"/>,
    call: <><path d="M4 13v-1a8 8 0 0 1 16 0v1M4 13H2v6h5v-6H4Zm16 0h2v6h-5v-6h3ZM19 19v2h-6"/></>,
    check: <path d="m5 12 4 4L19 6"/>,
    arrow: <path d="M4 12h15m-5-5 5 5-5 5"/>,
    list: <><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/></>,
    history: <><path d="M3 10a9 9 0 1 1 1 7M3 4v6h6M12 7v5l3 2"/></>,
    settings: <><path d="M4 6h16M4 12h16M4 18h16"/><circle cx="8" cy="6" r="2" fill="currentColor"/><circle cx="16" cy="12" r="2" fill="currentColor"/><circle cx="10" cy="18" r="2" fill="currentColor"/></>,
    close: <path d="m6 6 12 12M6 18 18 6"/>,
    file: <><path d="M14 3H5v18h14V8l-5-5Zm0 0v6h5M8 13h8M8 17h5"/></>,
    play: <path d="m9 5 11 7-11 7V5Z"/>,
    shield: <><path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z"/><path d="m8 12 3 3 5-6"/></>,
  }
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" style={style}>{paths[name]}</svg>
}
