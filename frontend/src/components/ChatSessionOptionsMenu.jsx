import React from 'react'
import { BsPinAngle } from 'react-icons/bs'
import { RiUnpinLine } from 'react-icons/ri'
import { HiOutlinePencil, HiOutlineTrash } from 'react-icons/hi'

export default function ChatSessionOptionsMenu({
  session,
  onClose,
  onTogglePin,
  onRename,
  onDelete,
}) {
  const run = (action) => (e) => {
    e.stopPropagation()
    onClose?.()
    action?.(session)
  }

  const items = [
    {
      key: 'pin',
      Icon: session.pinned ? RiUnpinLine : BsPinAngle,
      label: session.pinned ? 'Unpin chat' : 'Pin chat',
      action: onTogglePin,
      className: 'text-[#3d2b1f] hover:bg-[#f0ddb6]',
    },
    {
      key: 'rename',
      Icon: HiOutlinePencil,
      label: 'Rename',
      action: onRename,
      className: 'text-[#3d2b1f] hover:bg-[#f0ddb6]',
    },
    {
      key: 'delete',
      Icon: HiOutlineTrash,
      label: 'Delete chat',
      action: onDelete,
      className: 'text-red-800 hover:bg-red-900/10',
    },
  ]

  return (
    <ul
      className="absolute right-0 top-full z-20 mt-0.5 min-w-[10.5rem] rounded-xl border border-[#5C6E43]/20 bg-[#F6E7C8] p-1.5 shadow-xl text-sm"
      role="menu"
    >
      {items.map((entry) => {
        const { key, label, action, className } = entry
        const IconComp = entry.Icon
        return (
          <li key={key} role="none">
            <button
              type="button"
              role="menuitem"
              className={`w-full flex items-center rounded-md gap-2.5 cursor-pointer px-3 py-2 text-left ${className}`}
              onClick={run(action)}
            >
              <IconComp className="shrink-0 opacity-90" size={17} aria-hidden />
              <span>{label}</span>
            </button>
          </li>
        )
      })}
    </ul>
  )
}
