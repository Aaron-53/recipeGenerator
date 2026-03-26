import React, { useState, useCallback, useEffect, useLayoutEffect, useMemo, useRef } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import ChatHistory from '../components/ChatHistory'
import ChatArea from '../components/ChatArea'
import ConfirmDialog from '../components/ConfirmDialog'
import ErrorBanner from '../components/ErrorBanner'
import { chatAPI, chatSessionsAPI, inventoryAPI } from '../services/api'
import { deriveSessionTitle } from '../utils/parseRecipeContent'
import { formatApiError, isRequestAbortError } from '../utils/formatApiError'
import { useBodyScrollLock } from '../hooks/useBodyScrollLock'
import { GoSidebarCollapse, GoSidebarExpand } from 'react-icons/go'

function toApiMessages(messages) {
  return messages.map((m) => ({
    id: m.id || '',
    role: m.role,
    content: m.content,
  }))
}

function mapSessionMessages(messages) {
  if (!Array.isArray(messages)) return []
  return messages.map((m, i) => ({
    id: m.id || `m-${i}`,
    role: m.role,
    content: m.content,
  }))
}

function inventoryNamesFromResponse(invRes) {
  const rows = invRes?.data
  if (!Array.isArray(rows)) return []
  return rows.map((item) => String(item.name || '').trim()).filter(Boolean)
}

const Chat = () => {
  const location = useLocation()
  const navigate = useNavigate()
  const [promptSeed, setPromptSeed] = useState(null)
  const initialPrompt = location.state?.initialPrompt

  useLayoutEffect(() => {
    if (typeof initialPrompt === 'string' && initialPrompt.trim()) {
      setPromptSeed(initialPrompt.trim())
      navigate(location.pathname, { replace: true, state: {} })
    }
  }, [initialPrompt, location.pathname, navigate])

  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [typingSessionId, setTypingSessionId] = useState(null)
  const [sendError, setSendError] = useState(null)
  const [loadingSessions, setLoadingSessions] = useState(true)
  const [renameSessionId, setRenameSessionId] = useState(null)
  const [renameDraft, setRenameDraft] = useState('')
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [mobileHistoryOpen, setMobileHistoryOpen] = useState(false)

  const activeSessionIdRef = useRef(null)
  const sessionLoadAbortRef = useRef(null)
  useLayoutEffect(() => {
    activeSessionIdRef.current = activeSessionId
  }, [activeSessionId])

  const isTyping =
    typingSessionId != null && typingSessionId === activeSessionId

  const sortedSessions = useMemo(() => {
    return [...sessions].sort((a, b) => {
      const pa = a.pinned ? 1 : 0
      const pb = b.pinned ? 1 : 0
      if (pa !== pb) return pb - pa
      const ta = new Date(a.updated_at || 0).getTime()
      const tb = new Date(b.updated_at || 0).getTime()
      return tb - ta
    })
  }, [sessions])

  const activeIndex = useMemo(() => {
    if (!activeSessionId) return -1
    return sortedSessions.findIndex((s) => s.id === activeSessionId)
  }, [activeSessionId, sortedSessions])

  const pageHeadingTitle = useMemo(() => {
    if (!activeSessionId) return 'New chat'
    const s = sortedSessions.find((x) => x.id === activeSessionId)
    const stored = (s?.title || '').trim()
    if (messages.length > 0) {
      const derived = deriveSessionTitle(messages)
      if (derived && derived !== 'New chat') return derived
    }
    return stored || 'New chat'
  }, [activeSessionId, sortedSessions, messages])

  const persistSession = useCallback(async (sessionId, msgs) => {
    if (!sessionId) return
    const title = deriveSessionTitle(msgs)
    try {
      await chatSessionsAPI.save(sessionId, {
        title,
        messages: toApiMessages(msgs),
      })
      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId
            ? { ...s, title, updated_at: new Date().toISOString() }
            : s
        )
      )
    } catch (e) {
      console.error('Failed to save chat session', e)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoadingSessions(true)
      try {
        const { data } = await chatSessionsAPI.list()
        if (cancelled) return
        const list = Array.isArray(data) ? data : []
        setSessions(list)
        setActiveSessionId(null)
        setMessages([])
        setTypingSessionId(null)
      } catch (e) {
        console.error(e)
        if (!cancelled) setSendError('Could not load saved chats.')
      } finally {
        if (!cancelled) setLoadingSessions(false)
      }
    })()
    return () => {
      cancelled = true
      sessionLoadAbortRef.current?.abort()
    }
  }, [])

  useBodyScrollLock(mobileHistoryOpen)

  useEffect(() => {
    const mq = window.matchMedia('(min-width: 1024px)')
    const onChange = () => {
      if (mq.matches) setMobileHistoryOpen(false)
    }
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  useEffect(() => {
    if (!mobileHistoryOpen) return
    const onKey = (e) => {
      if (e.key === 'Escape') setMobileHistoryOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [mobileHistoryOpen])

  const closeMobileHistory = useCallback(() => setMobileHistoryOpen(false), [])

  const handleSelectSession = useCallback(
    async (index) => {
      const s = sortedSessions[index]
      if (!s || s.id === activeSessionId) {
        return
      }
      sessionLoadAbortRef.current?.abort()
      const ac = new AbortController()
      sessionLoadAbortRef.current = ac

      activeSessionIdRef.current = s.id
      setActiveSessionId(s.id)
      setSendError(null)
      setMessages([])

      try {
        const { data } = await chatSessionsAPI.get(s.id, { signal: ac.signal })
        if (
          sessionLoadAbortRef.current !== ac ||
          activeSessionIdRef.current !== s.id
        ) {
          return
        }
        setMessages(mapSessionMessages(data.messages))
      } catch (e) {
        if (isRequestAbortError(e)) return
        if (activeSessionIdRef.current !== s.id) return
        setSendError('Could not load this chat.')
      }
    },
    [sortedSessions, activeSessionId]
  )

  const handleSelectSessionMobile = useCallback(
    (index) => {
      closeMobileHistory()
      void handleSelectSession(index)
    },
    [handleSelectSession, closeMobileHistory]
  )

  const handleNewChat = useCallback(() => {
    setSendError(null)
    setRenameSessionId(null)
    setRenameDraft('')
    activeSessionIdRef.current = null
    setActiveSessionId(null)
    setMessages([])
  }, [])

  const handleNewChatMobile = useCallback(() => {
    handleNewChat()
    closeMobileHistory()
  }, [handleNewChat, closeMobileHistory])

  const handleTogglePin = useCallback(async (session) => {
    const next = !session.pinned
    try {
      await chatSessionsAPI.patch(session.id, { pinned: next })
      setSessions((prev) =>
        prev.map((s) =>
          s.id === session.id ? { ...s, pinned: next } : s
        )
      )
    } catch (e) {
      console.error(e)
      setSendError('Could not update pin.')
    }
  }, [])

  const handleRenameStart = useCallback((session) => {
    setRenameSessionId(session.id)
    setRenameDraft(session.title || 'New chat')
  }, [])

  const handleRenameCommit = useCallback(async () => {
    if (!renameSessionId) return
    const title = renameDraft.trim()
    if (!title) {
      setRenameSessionId(null)
      setRenameDraft('')
      return
    }
    try {
      await chatSessionsAPI.patch(renameSessionId, { title })
      setSessions((prev) =>
        prev.map((s) =>
          s.id === renameSessionId ? { ...s, title } : s
        )
      )
      setRenameSessionId(null)
      setRenameDraft('')
    } catch (e) {
      console.error(e)
      setSendError('Could not rename chat.')
    }
  }, [renameSessionId, renameDraft])

  const handleRenameCancel = useCallback(() => {
    setRenameSessionId(null)
    setRenameDraft('')
  }, [])

  const handleDeleteRequest = useCallback((session) => {
    setDeleteTarget({
      id: session.id,
      title: session.title || 'New chat',
    })
  }, [])

  const handleDeleteConfirm = useCallback(async () => {
    if (!deleteTarget) return
    const deletedId = deleteTarget.id
    try {
      await chatSessionsAPI.delete(deletedId)
      setSessions((prev) => prev.filter((s) => s.id !== deletedId))
      if (activeSessionId === deletedId) {
        activeSessionIdRef.current = null
        setActiveSessionId(null)
        setMessages([])
      }
      setDeleteTarget(null)
      if (renameSessionId === deletedId) {
        setRenameDraft('')
      }
      setRenameSessionId((rid) => (rid === deletedId ? null : rid))
    } catch (e) {
      console.error(e)
      setSendError('Could not delete chat.')
    }
  }, [deleteTarget, activeSessionId, renameSessionId])

  const handleDeleteCancel = useCallback(() => {
    setDeleteTarget(null)
  }, [])

  const handleSend = useCallback(
    async (text) => {
      const trimmed = text.trim()
      if (!trimmed) return

      let sessionId = activeSessionId
      if (!sessionId) {
        try {
          const { data: created } = await chatSessionsAPI.create({ title: 'New chat' })
          if (!created?.id) throw new Error('missing id')
          sessionId = created.id
          const row = {
            id: created.id,
            title: created.title,
            updated_at: created.updated_at,
            pinned: Boolean(created.pinned),
          }
          setSessions((prev) => [row, ...prev])
          activeSessionIdRef.current = created.id
          setActiveSessionId(created.id)
        } catch (e) {
          console.error(e)
          setSendError('Could not start a chat session. Try again.')
          return
        }
      }

      const historyForApi = messages.map((m) => ({
        role: m.role === 'assistant' ? 'assistant' : 'user',
        content: m.content,
      }))

      setSendError(null)
      const userId = crypto.randomUUID()
      const nextAfterUser = [...messages, { id: userId, role: 'user', content: trimmed }]
      setMessages(nextAfterUser)
      const targetSessionId = sessionId
      setTypingSessionId(targetSessionId)

      try {
        let invRes
        try {
          invRes = await inventoryAPI.getAllItems()
        } catch {
          invRes = { data: [] }
        }
        const inventory = inventoryNamesFromResponse(invRes)

        const { data } = await chatAPI.sendMessage({
          message: trimmed,
          history: historyForApi,
          inventory,
        })

        const botId = crypto.randomUUID()
        const withAssistant = [
          ...nextAfterUser,
          { id: botId, role: 'assistant', content: data.reply },
        ]
        if (activeSessionIdRef.current === targetSessionId) {
          setMessages(withAssistant)
        }
        await persistSession(targetSessionId, withAssistant)
      } catch (e) {
        const msg = formatApiError(e, e.message || 'Something went wrong')
        const errAssistant = [
          ...nextAfterUser,
          {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: `Sorry — I couldn’t reach the assistant. ${msg}`,
          },
        ]
        if (activeSessionIdRef.current === targetSessionId) {
          setSendError(msg)
          setMessages(errAssistant)
        }
        await persistSession(targetSessionId, errAssistant)
      } finally {
        setTypingSessionId((t) => (t === targetSessionId ? null : t))
      }
    },
    [messages, activeSessionId, persistSession]
  )

  return (
    <div className="min-h-screen bg-[#5b6d44] flex flex-col">
      <Navbar />
      <main className="flex-1 px-4 sm:px-10 pb-8 mx-auto w-full pt-5">
        <h1 className='lg:hidden max-w-[calc(100vw-5rem)] flex flex-row items-center gap-2 truncate px-2 py-4 text-xl font-semibold tracking-tight text-[#F2CEC2] sm:py-4 sm:text-2xl md:text-3xl'>
          <button
            type="button"
            className="shrink-0 rounded-lg p-1 text-[#F2CEC2] outline-none transition-opacity hover:opacity-90 focus-visible:ring-2 focus-visible:ring-[#F2CEC2]/50"
            aria-expanded={mobileHistoryOpen}
            aria-label={mobileHistoryOpen ? 'Close chat history' : 'Open chat history'}
            onClick={() => setMobileHistoryOpen((o) => !o)}
          >
            {mobileHistoryOpen ? (
              <GoSidebarExpand className="h-7 w-7 sm:h-8 sm:w-8" aria-hidden />
            ) : (
              <GoSidebarCollapse className="h-7 w-7 sm:h-8 sm:w-8" aria-hidden />
            )}
          </button>
          <span className="min-w-0 truncate">{pageHeadingTitle}</span>
        </h1>
        <ErrorBanner
          message={sendError}
          onDismiss={() => setSendError(null)}
          variant="chat"
          className="mb-2 max-w-3xl px-3"
        />
        <div className="relative flex flex-col gap-3 lg:flex-row lg:items-stretch">
          <div
            className={`fixed inset-0 z-[9980] bg-black/45 backdrop-blur-[1px] transition-opacity duration-300 lg:hidden ${
              mobileHistoryOpen ? 'opacity-100' : 'pointer-events-none opacity-0'
            }`}
            aria-hidden
            onClick={closeMobileHistory}
          />
          <div
            className={`fixed inset-y-0 left-0 z-[9981] flex w-[min(88vw,320px)] max-w-full flex-col transition-transform duration-300 ease-out lg:static lg:z-[20] lg:h-auto lg:w-[28%] lg:min-w-[200px] lg:max-w-[320px] lg:translate-x-0 lg:pointer-events-auto lg:flex-shrink-0 ${
              mobileHistoryOpen ? 'translate-x-0' : '-translate-x-full pointer-events-none'
            }`}
          >
            <ChatHistory
              sessions={sortedSessions}
              activeIndex={activeIndex}
              onSelect={handleSelectSessionMobile}
              onNewChat={handleNewChatMobile}
              onTogglePin={handleTogglePin}
              onRename={handleRenameStart}
              onDelete={handleDeleteRequest}
              renameSessionId={renameSessionId}
              renameDraft={renameDraft}
              onRenameDraftChange={setRenameDraft}
              onRenameCommit={handleRenameCommit}
              onRenameCancel={handleRenameCancel}
              loading={loadingSessions}
            />
          </div>
          <div className="relative z-0 min-w-0 flex-1">
            <ChatArea
              sessionId={activeSessionId}
              messages={messages}
              onSend={handleSend}
              isTyping={isTyping}
              promptSeed={promptSeed}
            />
          </div>
        </div>
      </main>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete chat?"
        onCancel={handleDeleteCancel}
        onConfirm={handleDeleteConfirm}
      >
        <p>
          <span className="font-medium text-[#3d2b1f]">
            “{deleteTarget?.title}”
          </span>{' '}
          will be removed permanently. This cannot be undone.
        </p>
      </ConfirmDialog>
    </div>
  )
}

export default Chat
