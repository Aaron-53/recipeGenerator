import { FiX } from 'react-icons/fi'

const VARIANT_CLASS = {
  default: 'border border-red-800/40 bg-red-950/70 text-red-100',
  chat: 'border border-red-800/30 bg-red-900/30 text-amber-100',
  auth: 'border border-red-900/50 bg-red-900/40 text-red-200',
  light: 'border border-red-300/80 bg-red-100/90 text-red-800',
}

export default function ErrorBanner({
  message,
  onDismiss,
  variant = 'default',
  className = '',
  centerMessage = false,
}) {
  const text =
    message == null ? '' : typeof message === 'string' ? message.trim() : String(message)
  if (!text) return null

  const surface = VARIANT_CLASS[variant] ?? VARIANT_CLASS.default

  return (
    <div
      role="alert"
      className={`flex items-start gap-2 rounded-xl py-2.5 pl-3 pr-2 text-sm ${surface} ${className}`.trim()}
    >
      <p
        className={`min-w-0 flex-1 leading-snug ${centerMessage ? 'text-center' : 'text-left'}`}
      >
        {text}
      </p>
      {onDismiss ? (
        <button
          type="button"
          onClick={onDismiss}
          className="-m-0.5 shrink-0 rounded-md p-1 text-current opacity-80 transition-opacity hover:bg-black/15 hover:opacity-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-current/50"
          aria-label="Dismiss alert"
        >
          <FiX size={18} strokeWidth={2} aria-hidden />
        </button>
      ) : null}
    </div>
  )
}
