import React, { useRef, useEffect, useState } from 'react'
import {
  HiOutlineThumbDown,
  HiOutlineThumbUp,
  HiThumbDown,
  HiThumbUp,
} from 'react-icons/hi'
import { IoArrowUp } from 'react-icons/io5'

function BotRatingRow({ rating, onRate }) {
  const upOn = rating === 'up'
  const downOn = rating === 'down'
  const unset = rating == null
  const showUp = unset || upOn
  const showDown = unset || downOn

  const btn = 'rounded-md p-1 text-[#ffb300] transition-colors hover:bg-[#ffb300]/10 focus:outline-none cursor-pointer'

  return (
    <div className="flex flex-wrap items-center gap-1">
      <span className="text-xs text-[#3d2b1f]/75">How did the AI do?</span>
      <div className="flex min-h-[28px] items-center gap-">
        {showUp && (
          <button
            type="button"
            aria-label={upOn ? 'Remove rating' : 'Good response'}
            aria-pressed={upOn}
            onClick={() => onRate('up')}
            className={btn}
          >
            {upOn ? <HiThumbUp size={15} /> : <HiOutlineThumbUp size={16} />}
          </button>
        )}
        {showDown && (
          <button
            type="button"
            aria-label={downOn ? 'Remove rating' : 'Poor response'}
            aria-pressed={downOn}
            onClick={() => onRate('down')}
            className={btn}
          >
            {downOn ? <HiThumbDown size={15} /> : <HiOutlineThumbDown size={15} />}
          </button>
        )}
      </div>
    </div>
  )
}

const ChatArea = ({ messages, onSend, isTyping = false }) => {
  const [input, setInput] = useState('')
  const [ratings, setRatings] = useState({})
  const scrollRef = useRef(null)

  const rateKey = (msg, i) => msg.id ?? `bot-${i}`

  const handleRate = (key, dir) => {
    setRatings((prev) => {
      const next = { ...prev }
      if (next[key] === dir) delete next[key]
      else next[key] = dir
      return next
    })
  }

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, isTyping])

  const hasMessages = messages.length > 0

  const sendMessage = () => {
    const trimmed = input.trim()
    if (!trimmed) return
    onSend?.(trimmed)
    setInput('')
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    sendMessage()
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <section
      className="flex min-w-0 flex-1 flex-col rounded-[24px] bg-[#F6E7C8] shadow-md border border-[#e8dcc4]/80 overflow-hidden h-[calc(100vh-9rem)]"
    >
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 py-6 chat-area-scroll"
      >
        {!hasMessages ? (
          <div className="flex h-full min-h-[200px] items-center justify-center px-4">
            <p
              className="text-center text-2xl sm:text-3xl md:text-4xl font-bold text-[#5C6E43] leading-tight"
            >
              What are we making today?
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-4 pb-2">
            {messages.map((msg, i) =>
              msg.role === 'user' ? (
                <div key={msg.id ?? `u-${i}`} className="flex justify-end">
                  <div className="max-w-[85%] rounded-xl rounded-br-none bg-[#f4b9b2] px-4 py-2 text-[#3d2b1f] text-sm sm:text-base shadow-sm">
                    {msg.content}
                  </div>
                </div>
              ) : (
                <div key={msg.id ?? `b-${i}`} className="flex w-full justify-start">
                  <div className="max-w-[min(90%,32rem)]">
                    <div className="text-[#3d2b1f] text-sm sm:text-base whitespace-pre-wrap leading-relaxed">
                      {msg.content}
                    </div>
                    <BotRatingRow
                      rating={ratings[rateKey(msg, i)]}
                      onRate={(dir) => handleRate(rateKey(msg, i), dir)}
                    />
                  </div>
                </div>
              )
            )}
            {isTyping && (
              <div className="flex justify-start">
                <div
                  className="inline-flex items-center gap-1.5 rounded-2xl px-4 py-3 text-[#3d2b1f]/80"
                  aria-live="polite"
                  aria-label="Assistant is typing"
                >
                  <span className="sr-only">Assistant is typing</span>
                  <span className="flex gap-1">
                    <span className="h-2 w-2 animate-bounce rounded-full bg-[#5C6E43]/70 [animation-delay:0ms]" />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-[#5C6E43]/70 [animation-delay:150ms]" />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-[#5C6E43]/70 [animation-delay:300ms]" />
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="mt-auto p-3 bg-[#f5e8c7]">
        <div className="overflow-hidden rounded-2xl">
          <div className="flex min-h-24 items-end gap-3 p-2 bg-[#F6C7B7]">
            <label htmlFor="chat-input" className="sr-only">
              Message
            </label>
            <textarea
              id="chat-input"
              rows={3}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask or search anything"
              className="inventory-rows-scroll min-h-18 max-h-[min(40vh,14rem)] min-w-0 flex-1 resize-none overflow-y-auto rounded-xl bg-transparent px-1 py-0.5 text-[#3d2b1f] placeholder:italic placeholder:text-[#3d2b1f]/55 focus:outline-none text-sm sm:text-base leading-relaxed"
            />
            <button
              type="submit"
              disabled={!input.trim()}
              className="flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center rounded-full bg-[#F6E7C8] text-[#3d2b1f] shadow-md transition-opacity hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-50"
              aria-label="Send message"
            >
              <IoArrowUp size={20} />
            </button>
          </div>
        </div>
      </form>
    </section>
  )
}

export default ChatArea
