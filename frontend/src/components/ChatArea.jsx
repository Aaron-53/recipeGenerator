import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react'
import {
  HiOutlineThumbDown,
  HiOutlineThumbUp,
  HiThumbDown,
  HiThumbUp,
} from 'react-icons/hi'
import { IoArrowUp } from 'react-icons/io5'
import RatingDialog from './RatingDialog'
import RecipeCard from './RecipeCard'
import { chatAPI } from '../services/api'
import {
  parseAssistantMessage,
  buildIntroSegments,
} from '../utils/parseRecipeContent'

function BotRatingRow({ disabled, onOpenDialog, thumbChosen }) {
  const btn =
    'rounded-md p-1 text-[#E69695] transition-colors hover:bg-[#E69695]/10 focus:outline-none cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed'
  const btnFilled =
    'rounded-md p-1 text-[#E69695] cursor-default focus:outline-none'

  const unset = thumbChosen == null

  const statusText = unset
    ? 'How was this recipe?'
    : thumbChosen === 'up'
      ? 'Thanks for the rating!'
      : "Sorry, we'll improve next time!"

  return (
    <div className="flex flex-wrap items-center gap-1 mt-2">
      <span className="text-xs text-[#3d2b1f]/75">{statusText}</span>
      <div className="flex min-h-[28px] items-center gap-1">
        {unset && (
          <>
            <button
              type="button"
              aria-label="Rate positively"
              onClick={() => onOpenDialog('up')}
              disabled={disabled}
              className={btn}
            >
              <HiOutlineThumbUp size={16} />
            </button>
            <button
              type="button"
              aria-label="Rate negatively"
              onClick={() => onOpenDialog('down')}
              disabled={disabled}
              className={btn}
            >
              <HiOutlineThumbDown size={15} />
            </button>
          </>
        )}
        {thumbChosen === 'up' && (
          <span className={btnFilled} role="img" aria-label="You rated (thumbs up)">
            <HiThumbUp size={15} />
          </span>
        )}
        {thumbChosen === 'down' && (
          <span className={btnFilled} role="img" aria-label="You rated (thumbs down)">
            <HiThumbDown size={15} />
          </span>
        )}
      </div>
    </div>
  )
}

function AssistantIntro({
  intro,
  recipeName,
  anchorId,
}) {
  const segments = useMemo(
    () => buildIntroSegments(intro, recipeName),
    [intro, recipeName]
  )

  const jumpToRecipe = () => {
    document
      .getElementById(anchorId)
      ?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }

  return (
    <div className="text-[#3d2b1f] text-sm sm:text-base whitespace-pre-wrap leading-relaxed mb-2 break-words">
      {segments.map((seg, i) => {
        if (seg.type === 'recipeLink') {
          return (
            <button
              key={i}
              type="button"
              onClick={jumpToRecipe}
              className="inline font-semibold text-[#5C6E43] underline decoration-[#5C6E43]/45 underline-offset-2 hover:bg-[#5C6E43]/12 rounded px-0.5 -mx-0.5 align-baseline cursor-pointer"
            >
              {seg.text}
            </button>
          )
        }
        if (seg.type === 'bold') {
          return (
            <strong key={i} className="font-semibold text-[#3d2b1f]">
              {seg.text}
            </strong>
          )
        }
        return <span key={i}>{seg.text}</span>
      })}
    </div>
  )
}

const ChatArea = ({
  sessionId = null,
  messages,
  onSend,
  isTyping = false,
  promptSeed = null,
}) => {
  const [input, setInput] = useState('')
  const [ratedThumbByKey, setRatedThumbByKey] = useState(() => new Map())
  const [dialog, setDialog] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)
  const scrollRef = useRef(null)

  useEffect(() => {
    setRatedThumbByKey(new Map())
  }, [sessionId])

  useEffect(() => {
    if (promptSeed == null || promptSeed === '') return
    setInput(promptSeed)
  }, [promptSeed])

  const rateKey = (msg, i) => msg.id ?? `assistant-${i}`

  const openDialog = (key, recipeText, hint) => {
    setSubmitError(null)
    setDialog({ key, recipeText, hint })
  }

  const handleSubmitRating = useCallback(
    async (rating, review) => {
      if (!dialog) return
      setSubmitting(true)
      setSubmitError(null)
      try {
        await chatAPI.rateRecipe({
          recipe_text: dialog.recipeText,
          rating,
          review: review || '',
        })
        setRatedThumbByKey((prev) =>
          new Map(prev).set(dialog.key, dialog.hint)
        )
        setDialog(null)
      } catch (e) {
        const msg =
          e.response?.data?.detail ||
          e.message ||
          'Could not save rating. Try again.'
        setSubmitError(typeof msg === 'string' ? msg : JSON.stringify(msg))
      } finally {
        setSubmitting(false)
      }
    },
    [dialog]
  )

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
      <RatingDialog
        isOpen={!!dialog}
        onClose={() => !submitting && setDialog(null)}
        onSubmit={handleSubmitRating}
        isSubmitting={submitting}
        error={submitError}
        onDismissError={() => setSubmitError(null)}
      />

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 lg:px-12 py-6 chat-area-scroll"
      >
        {!hasMessages ? (
          <div className="flex flex-col text-center text-2xl sm:text-3xl md:text-4xl font-bold text-[#5C6E43] leading-tight h-[calc(100vh-17rem)] lg:h-[200px] items-center justify-center px-4">
              What are we making today?
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
                <div key={msg.id ?? `a-${i}`} className="flex w-full justify-start">
                  <div className="w-full">
                    {(() => {
                      const { intro, recipe } = parseAssistantMessage(msg.content)
                      if (recipe) {
                        const anchorId = `assistant-recipe-${String(
                          msg.id ?? `idx-${i}`
                        ).replace(/[^a-zA-Z0-9_-]/g, '-')}`
                        return (
                          <>
                            {intro ? (
                              <AssistantIntro
                                intro={intro}
                                recipeName={recipe.recipe_name}
                                anchorId={anchorId}
                              />
                            ) : null}
                            <RecipeCard recipe={recipe} anchorId={anchorId} />
                          </>
                        )
                      }
                      return (
                        <div className="text-[#3d2b1f] text-sm sm:text-base whitespace-pre-wrap leading-relaxed">
                          {msg.content}
                        </div>
                      )
                    })()}
                    <BotRatingRow
                      disabled={isTyping}
                      thumbChosen={ratedThumbByKey.get(rateKey(msg, i)) ?? null}
                      onOpenDialog={(hint) =>
                        openDialog(rateKey(msg, i), msg.content, hint)
                      }
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

      <form onSubmit={handleSubmit} className="mt-auto pb-4 px-4 lg:px-8 bg-[#f5e8c7]">
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
              disabled={isTyping}
              className="inventory-rows-scroll min-h-18 max-h-[min(40vh,14rem)] min-w-0 flex-1 resize-none overflow-y-auto rounded-xl bg-transparent px-1 py-0.5 text-[#3d2b1f] placeholder:italic placeholder:text-[#3d2b1f]/55 focus:outline-none text-sm sm:text-base leading-relaxed disabled:cursor-not-allowed disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={!input.trim() || isTyping}
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
