import React, { useEffect, useId } from 'react'
import { FiX } from 'react-icons/fi'

export default function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel = 'Delete',
  cancelLabel = 'Cancel',
  onConfirm,
  onCancel,
  danger = true,
  zIndexClass = 'z-50',
}) {
  const titleId = useId()

  useEffect(() => {
    if (!open) return
    const onEsc = (e) => {
      if (e.key === 'Escape') onCancel?.()
    }
    document.addEventListener('keydown', onEsc)
    return () => document.removeEventListener('keydown', onEsc)
  }, [open, onCancel])

  if (!open) return null

  return (
    <div
      className={`fixed inset-0 ${zIndexClass} flex items-center justify-center bg-black/40 p-4`}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel?.()
      }}
    >
      <div
        className="w-full max-w-md rounded-xl bg-[#F6E7C8] p-5 shadow-xl border border-[#5C6E43]/20"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 mb-3">
          <h2
            id={titleId}
            className="text-xl font-semibold text-[#5C6E43] pr-2"
          >
            {title}
          </h2>
          <button
            type="button"
            onClick={onCancel}
            className="p-1.5 rounded-lg text-[#5C6E43] hover:text-[#475434] transition-colors cursor-pointer shrink-0 -mt-1 -mr-1"
            aria-label="Close"
          >
            <FiX size={22} />
          </button>
        </div>
        <div className="text-base text-[#3d2b1f]/90 mb-6">{children}</div>
        <div className="flex justify-between gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-xl w-full cursor-pointer border border-[#5C6E43]/30 px-4 py-2 text-base font-medium text-[#5C6E43] hover:bg-[#5C6E43]/10"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className={`rounded-xl w-full cursor-pointer px-4 py-2 text-base font-semibold text-white ${
              danger
                ? 'border-2 !text-red-800 border-red-800 hover:bg-red-900/20'
                : 'bg-[#5C6E43] hover:bg-[#4a5a36]'
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
