import React, { useEffect, useState } from 'react'
import { FaRegEdit } from 'react-icons/fa'
import { HiOutlineDotsHorizontal } from 'react-icons/hi'
import { RiPushpinFill } from "react-icons/ri";
import Loader from './Loader'
import ChatSessionOptionsMenu from './ChatSessionOptionsMenu'

const ChatHistory = ({
  sessions = [],
  activeIndex = -1,
  onSelect,
  onNewChat,
  onTogglePin,
  onRename,
  onDelete,
  renameSessionId = null,
  renameDraft = '',
  onRenameDraftChange,
  onRenameCommit,
  onRenameCancel,
  loading = false,
  className = '',
}) => {
  const [menuOpenId, setMenuOpenId] = useState(null)

  useEffect(() => {
    if (!menuOpenId) return
    const close = (e) => {
      const root = e.target.closest?.('[data-chat-menu-root]')
      if (root?.dataset?.chatId === menuOpenId) return
      setMenuOpenId(null)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [menuOpenId])

  const hasHistory = Array.isArray(sessions) && sessions.length > 0

  return (
    <aside
      className={`flex h-full min-h-0 w-full min-w-0 flex-col overflow-hidden lg:rounded-[24px] bg-[#F6E7C8] shadow-md lg:h-[calc(100vh-9rem)] ${className}`.trim()}
    >
      <div className="lg:rounded-t-[24px] bg-[#F6C7B7] px-3 py-8 lg:py-4 shrink-0">
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-x-2">
          <div aria-hidden className="min-w-0" />
          <h2 className="text-center text-[#5C6E43] font-semibold text-2xl min-w-0">
            Chat history
          </h2>
          <div className="flex min-w-0 justify-end">
            {onNewChat && (
              <button
                type="button"
                onClick={onNewChat}
                disabled={loading}
                aria-label="New chat"
                title="New chat"
                className="inline-flex shrink-0 cursor-pointer items-center justify-center rounded-full p-1.5 text-[#5C6E43] hover:bg-[#5C6E43]/10 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <FaRegEdit size={19} />
              </button>
            )}
          </div>
        </div>
      </div>
      {loading ? (
        <Loader className="flex-1 min-h-0" color="#5C6E43" size="sm" />
      ) : hasHistory ? (
        <ul className="flex-1 overflow-y-auto p-2 space-y-1.5 chat-history-scroll min-h-0">
          {sessions.map((s, index) => (
            <li key={s.id}>
              <div
                className={`group flex items-stretch gap-0.5 rounded-xl transition-colors ${
                  index === activeIndex && activeIndex >= 0
                    ? 'bg-[#f0ddb6]'
                    : 'bg-[#F6E7C8] hover:bg-[#f0ddb6]/50'
                }`}
              >
                {renameSessionId === s.id ? (
                  <input
                    autoFocus
                    type="text"
                    value={renameDraft}
                    onChange={(e) => onRenameDraftChange?.(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        onRenameCommit?.()
                      } else if (e.key === 'Escape') {
                        e.preventDefault()
                        onRenameCancel?.()
                      }
                    }}
                    onBlur={() => onRenameCancel?.()}
                    maxLength={120}
                    aria-label="Rename chat"
                    className="flex-1 min-w-0 rounded-lg border border-[#5C6E43]/35 bg-transparent py-2 pl-3 pr-1 text-sm font-medium text-[#5C6E43] shadow-inner outline-none focus:border-[#5C6E43]/60 focus:ring-1 focus:ring-[#5C6E43]/30"
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <button
                    type="button"
                    onClick={() => onSelect?.(index)}
                    className="flex-1 min-w-0 cursor-pointer text-left rounded-l-xl truncate py-3 pl-3 pr-1 text-sm font-medium text-[#5C6E43]"
                  >
                    <span className="truncate">{s.title || 'New chat'}</span>
                  </button>
                )}
                <div
                  className="relative flex w-10 shrink-0 items-center justify-end self-stretch pr-1"
                  data-chat-menu-root
                  data-chat-id={s.id}
                >
                  {s.pinned && (
                    <span
                      className={`pointer-events-none absolute top-1/2 -translate-y-1/2 transition-[right] duration-200 ease-out ${
                        menuOpenId === s.id
                          ? 'right-9'
                          : 'right-0 group-hover:right-9 group-focus-within:right-9'
                      }`}
                      aria-hidden
                    >
                      <RiPushpinFill
                        className="text-[#5C6E43] mr-3"
                        size={16}
                        aria-label="Pinned"
                      />
                    </span>
                  )}
                  <button
                    type="button"
                    aria-label="Chat options"
                    aria-expanded={menuOpenId === s.id}
                    onClick={(e) => {
                      e.stopPropagation()
                      setMenuOpenId((id) => (id === s.id ? null : s.id))
                    }}
                    className={`relative z-10 rounded-lg p-1.5 text-[#5C6E43] hover:bg-[#5C6E43]/10 focus:outline-none cursor-pointer transition-opacity duration-150 focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-[#5C6E43]/40 ${
                      menuOpenId === s.id
                        ? 'opacity-100'
                        : 'opacity-0 group-hover:opacity-100 group-focus-within:opacity-100'
                    }`}
                  >
                    <HiOutlineDotsHorizontal size={18} />
                  </button>
                  {menuOpenId === s.id && (
                    <ChatSessionOptionsMenu
                      session={s}
                      onClose={() => setMenuOpenId(null)}
                      onTogglePin={onTogglePin}
                      onRename={onRename}
                      onDelete={onDelete}
                    />
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center px-5 py-10 text-center min-h-0">
          <p className="text-[#3d2b1f]/70 text-sm leading-relaxed max-w-[220px]">
            No history to show yet.
          </p>
          <p className="text-[#5b6d44] font-semibold text-sm sm:text-base mt-3">
            Start cooking today!
          </p>
        </div>
      )}
    </aside>
  )
}

export default ChatHistory
