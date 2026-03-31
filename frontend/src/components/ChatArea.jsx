import React, {
  useRef,
  useEffect,
  useState,
  useCallback,
  useMemo,
} from 'react'
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
  splitIntroMarkdown,
} from '../utils/parseRecipeContent'

function getRecipeTarget(msg, rateKey, pickByKey) {
  const picked = pickByKey.get(rateKey)
  if (picked?.point_id) return picked
  const list = msg.ranked_suggestions
  if (Array.isArray(list) && list.length > 0) {
    const pid = msg.point_id != null ? String(msg.point_id) : ''
    if (pid) {
      const match = list.find((s) => String(s.point_id) === pid)
      if (match) {
        return {
          point_id: String(match.point_id),
          recipe_id: String(match.recipe_id || match.point_id),
        }
      }
    }
    const s = list[0]
    return {
      point_id: String(s.point_id),
      recipe_id: String(s.recipe_id || s.point_id),
    }
  }
  if (msg.point_id) {
    return {
      point_id: String(msg.point_id),
      recipe_id: String(msg.recipe_id || msg.point_id),
    }
  }
  return { point_id: null, recipe_id: null }
}

function resolveRatingTarget(msg, rateKey, pickByKey, msgIndex, allMessages) {
  const t = getRecipeTarget(msg, rateKey, pickByKey)
  if (t.point_id) return t
  if (!Array.isArray(allMessages) || msgIndex == null || msgIndex < 1) {
    return { point_id: null, recipe_id: null }
  }
  for (let k = msgIndex - 1; k >= 0; k--) {
    const m = allMessages[k]
    if (m.role !== 'assistant') continue
    if (m.point_id != null && String(m.point_id).trim()) {
      return {
        point_id: String(m.point_id),
        recipe_id:
          m.recipe_id != null ? String(m.recipe_id) : String(m.point_id),
      }
    }
    const rs = m.ranked_suggestions
    if (Array.isArray(rs) && rs.length > 0 && rs[0]?.point_id != null) {
      const s0 = rs[0]
      return {
        point_id: String(s0.point_id),
        recipe_id: String(s0.recipe_id || s0.point_id),
      }
    }
  }
  return { point_id: null, recipe_id: null }
}

function buildDisplayRecipe(msg, rateKey, pickByKey, parsedRecipe) {
  const target = getRecipeTarget(msg, rateKey, pickByKey)
  const list = msg.ranked_suggestions || []
  if (list.length === 0) {
    if (parsedRecipe) {
      return {
        recipe: {
          recipe_name: parsedRecipe.recipe_name || 'Recipe',
          ingredients: Array.isArray(parsedRecipe.ingredients) ? parsedRecipe.ingredients : [],
          steps: Array.isArray(parsedRecipe.steps) ? parsedRecipe.steps : [],
          tips: parsedRecipe.tips != null ? String(parsedRecipe.tips) : '',
        },
        showLibraryHint: false,
        cardTitle: parsedRecipe.recipe_name || null,
      }
    }
    return { recipe: null, showLibraryHint: false, cardTitle: null }
  }

  let sug = list.find((s) => String(s.point_id) === String(target.point_id))
  if (!sug) sug = list[0]

  const hasDbBody =
    (Array.isArray(sug.ingredients) && sug.ingredients.length > 0) ||
    (Array.isArray(sug.steps) && sug.steps.length > 0) ||
    (sug.tips && String(sug.tips).trim()) ||
    !!(sug.title && String(sug.title).trim())

  if (!hasDbBody && !parsedRecipe) {
    const name = (sug.title || 'Recipe').trim() || 'Recipe'
    return {
      recipe: {
        recipe_name: name,
        ingredients: [],
        steps: [],
        tips:
          'Select an option above to see the full ingredients and steps.',
      },
      showLibraryHint: true,
      cardTitle: name,
    }
  }

  const name = (sug.title || parsedRecipe?.recipe_name || 'Recipe').trim()
  const ingredients =
    sug.ingredients?.length > 0
      ? sug.ingredients
      : parsedRecipe?.ingredients || []
  const steps =
    sug.steps?.length > 0
      ? sug.steps
      : hasDbBody
        ? []
        : parsedRecipe?.steps || []
  const tips =
    (parsedRecipe?.tips != null && String(parsedRecipe.tips).trim()) ||
    (sug.tips && String(sug.tips).trim()) ||
    ''

  return {
    recipe: {
      recipe_name: name,
      ingredients: Array.isArray(ingredients) ? ingredients : [],
      steps: Array.isArray(steps) ? steps : [],
      tips,
    },
    showLibraryHint: hasDbBody,
    cardTitle: name,
  }
}

const SUGGEST_BTN_BASE =
  'w-full cursor-pointer rounded-lg border px-3 py-2 text-left text-xs text-[#3d2b1f] transition-colors'
const SUGGEST_BTN_ON = 'border-[#5C6E43] bg-[#5C6E43]/15'
const SUGGEST_BTN_OFF =
  'border-[#e8dcc4] bg-white/50 hover:border-[#5C6E43]/50'

function RecipeSuggestionsPicker({
  suggestions,
  selectedPointId,
  disabled,
  onSelect,
}) {
  if (!Array.isArray(suggestions) || suggestions.length < 2) return null

  const sel = selectedPointId != null ? String(selectedPointId) : ''

  return (
    <div className="mb-1 mt-2 rounded-xl border border-[#5C6E43]/25 bg-[#f5e8c7]/80 px-3 py-2">
      <div className="flex w-full gap-3">
        {suggestions.map((s, idx) => {
          const active = String(s.point_id) === sel
          return (
            <button
              key={s.point_id != null ? String(s.point_id) : `opt-${idx}`}
              type="button"
              disabled={disabled}
              onClick={() => onSelect(s)}
              className={`${SUGGEST_BTN_BASE} ${active ? SUGGEST_BTN_ON : SUGGEST_BTN_OFF}`}
            >
              <span className="line-clamp-3 font-semibold">
                {s.title?.trim() || `Option ${idx + 1}`}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

function BotRatingRow({ disabled, onThumbClick, thumbChosen, barError }) {
  const btn =
    'rounded-md p-1 text-[#E69695] transition-colors hover:bg-[#E69695]/10 focus:outline-none cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed'
  const btnChosenUp =
    'rounded-md p-1 text-[#E69695] transition-colors focus:outline-none cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed bg-[#E69695]/15'
  const btnChosenDown =
    'rounded-md p-1 text-[#E69695] transition-colors focus:outline-none cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed bg-[#E69695]/15'

  const statusText ='How was the recipe?'

  const showBoth = thumbChosen == null

  return (
    <div className="flex flex-col gap-1 mt-2">
      <div className="flex flex-wrap items-center gap-1">
        <span className="text-xs text-[#3d2b1f]/75">{statusText}</span>
        <div className="flex min-h-[28px] items-center gap-1">
          {(showBoth || thumbChosen === 'up') && (
            <button
              type="button"
              aria-label="Rate positively"
              onClick={() => onThumbClick('up')}
              disabled={disabled}
              className={thumbChosen === 'up' ? btnChosenUp : btn}
            >
              {thumbChosen === 'up' ? <HiThumbUp size={16} /> : <HiOutlineThumbUp size={16} />}
            </button>
          )}
          {(showBoth || thumbChosen === 'down') && (
            <button
              type="button"
              aria-label="Rate negatively"
              onClick={() => onThumbClick('down')}
              disabled={disabled}
              className={thumbChosen === 'down' ? btnChosenDown : btn}
            >
              {thumbChosen === 'down' ? <HiThumbDown size={15} /> : <HiOutlineThumbDown size={15} />}
            </button>
          )}
        </div>
      </div>
      {barError ? (
        <p className="text-xs text-red-700/90 max-w-md">{barError}</p>
      ) : null}
    </div>
  )
}

function PlainAssistantMarkdown({ text }) {
  const parts = useMemo(() => splitIntroMarkdown(text ?? ''), [text])
  return (
    <div className="text-[#3d2b1f] text-sm sm:text-base whitespace-pre-wrap leading-relaxed break-words">
      {parts.map((p, i) =>
        p.type === 'bold' ? (
          <strong key={i} className="font-semibold text-[#3d2b1f]">
            {p.text}
          </strong>
        ) : (
          <span key={i}>{p.text}</span>
        )
      )}
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

export default function ChatArea({
  sessionId = null,
  messages,
  onSend,
  isTyping = false,
  promptSeed = null,
  sessionMeta = {},
  onRegisterActions,
  sessionRatingRequest = null,
  onSessionRatingRequestConsumed,
  onRecipeSelection,
  onThumbRatingsChange,
}) {
  const [input, setInput] = useState('')
  const [ratedThumbByKey, setRatedThumbByKey] = useState(() => new Map())
  const ratedThumbByKeyRef = useRef(ratedThumbByKey)
  ratedThumbByKeyRef.current = ratedThumbByKey
  const [pickByKey, setPickByKey] = useState(() => new Map())
  const [barErrorByKey, setBarErrorByKey] = useState(() => new Map())
  const [dialog, setDialog] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)
  const scrollRef = useRef(null)

  const pickByKeyRef = useRef(pickByKey)
  pickByKeyRef.current = pickByKey
  const messagesRef = useRef(messages)
  messagesRef.current = messages

  const flushedSelectionRef = useRef(new Map())
  const rateKey = (msg, i) => msg.id ?? `assistant-${i}`

  const flushSelectionForMessage = useCallback(async (msgKey, msg, picked = null) => {
    const t = picked
      ? {
          point_id: String(picked.point_id),
          recipe_id: String(picked.recipe_id || picked.point_id),
        }
      : getRecipeTarget(msg, msgKey, pickByKeyRef.current)
    if (!t.point_id) return
    const pid = String(t.point_id)
    if (flushedSelectionRef.current.get(msgKey) === pid) return
    console.log('[ChatArea] commit recipe selection (feedback)', {
      msgKey,
      point_id: pid,
      recipe_id: t.recipe_id,
    })
    await chatAPI.postFeedback({
      action: 'selected',
      point_id: pid,
      recipe_id: t.recipe_id || undefined,
    })
    await chatAPI.postMetrics({
      event: 'recipe_suggestion_selected',
      recipe_id: String(t.recipe_id || t.point_id),
      extra: { source: picked ? 'last_selected' : 'send_flush' },
    })
    flushedSelectionRef.current.set(msgKey, pid)
  }, [])

  const flushPendingSelections = useCallback(async () => {
    const msgs = messagesRef.current
    const picks = pickByKeyRef.current
    for (let i = 0; i < msgs.length; i++) {
      const msg = msgs[i]
      if (msg.role !== 'assistant' || !msg.ranked_suggestions?.length) continue
      const key = rateKey(msg, i)
      try {
        await flushSelectionForMessage(key, msg)
        const t = getRecipeTarget(msg, key, picks)
        if (t.point_id && msg.id) {
          onRecipeSelection?.(msg.id, {
            point_id: String(t.point_id),
            recipe_id: String(t.recipe_id || t.point_id),
          })
        }
      } catch (e) {
        console.error('[ChatArea] flushSelectionForMessage', key, e)
      }
    }
  }, [flushSelectionForMessage, onRecipeSelection])

  useEffect(() => {
    if (!onRegisterActions) return
    onRegisterActions({ flushPendingSelections })
    return () => onRegisterActions(null)
  }, [onRegisterActions, flushPendingSelections])

  useEffect(() => {
    setPickByKey(new Map())
    setBarErrorByKey(new Map())
    flushedSelectionRef.current.clear()
  }, [sessionId])

  const thumbRatingsJson = JSON.stringify(sessionMeta?.thumb_ratings ?? {})
  useEffect(() => {
    try {
      const tr = JSON.parse(thumbRatingsJson)
      if (tr && typeof tr === 'object' && !Array.isArray(tr)) {
        setRatedThumbByKey(new Map(Object.entries(tr)))
      } else {
        setRatedThumbByKey(new Map())
      }
    } catch {
      setRatedThumbByKey(new Map())
    }
  }, [sessionId, thumbRatingsJson])

  useEffect(() => {
    if (promptSeed == null || promptSeed === '') return
    setInput(promptSeed)
  }, [promptSeed])

  const openDialog = (key, recipeText, pointId, recipeId, hint) => {
    setSubmitError(null)
    setDialog({ key, recipeText, pointId, recipeId, hint })
  }

  const sessionRatingOpenSigRef = useRef(null)
  useEffect(() => {
    if (!sessionRatingRequest) {
      sessionRatingOpenSigRef.current = null
      return
    }
    const sig = `${sessionRatingRequest.messageId ?? ''}|${sessionRatingRequest.pointId ?? ''}`
    if (sessionRatingOpenSigRef.current === sig) return
    sessionRatingOpenSigRef.current = sig
    console.log('[ChatArea] session wrapup → open rating dialog', {
      hasPointId: Boolean(sessionRatingRequest.pointId),
    })
    setSubmitError(null)
    setDialog({
      key: `session-rating-${sessionRatingRequest.messageId ?? 'wrap'}`,
      recipeText: sessionRatingRequest.recipeText,
      pointId: sessionRatingRequest.pointId,
      recipeId: sessionRatingRequest.recipeId,
      hint: 'up',
    })
    onSessionRatingRequestConsumed?.()
  }, [sessionRatingRequest, onSessionRatingRequestConsumed])

  const handleSubmitRating = useCallback(
    async (rating, review) => {
      if (!dialog) return
      setSubmitting(true)
      setSubmitError(null)
      try {
        const entryHint = dialog.hint === 'down' ? 'down' : 'up'
        const thumbFromStars = rating >= 3 ? 'up' : 'down'
        console.log('[ChatArea] submit rating dialog', {
          rating,
          entryHint,
          thumbFromStars,
          point_id: dialog.pointId,
          recipe_id: dialog.recipeId,
        })
        await chatAPI.rateRecipe({
          recipe_text: dialog.recipeText,
          rating,
          review: review || '',
          ...(dialog.pointId ? { point_id: String(dialog.pointId) } : {}),
        })
        if (dialog.pointId) {
          await chatAPI.postFeedback({
            action: 'rating',
            point_id: String(dialog.pointId),
            recipe_id: dialog.recipeId || undefined,
            rating_value: rating,
          })
          await chatAPI.postMetrics({
            event: 'star_rating',
            recipe_id: String(dialog.recipeId || dialog.pointId),
            extra: { rating, thumb: thumbFromStars, entry_hint: entryHint },
          })
        }
        setRatedThumbByKey((prev) => new Map(prev).set(dialog.key, thumbFromStars))
        onThumbRatingsChange?.(dialog.key, thumbFromStars)
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
    [dialog, onThumbRatingsChange]
  )

  const handlePickSuggestion = useCallback(
    (rateKeyStr, s, msg) => {
      const picked = {
        point_id: String(s.point_id),
        recipe_id: String(s.recipe_id || s.point_id),
      }
      setPickByKey((prev) => new Map(prev).set(rateKeyStr, picked))
      setBarErrorByKey((prev) => new Map(prev).set(rateKeyStr, ''))
      if (msg?.id) onRecipeSelection?.(msg.id, picked)
      void flushSelectionForMessage(rateKeyStr, msg, picked).catch((e) =>
        console.error('[ChatArea] selection commit', e)
      )
    },
    [flushSelectionForMessage, onRecipeSelection]
  )

  const handleOpenRating = useCallback(
    (key, msg, hint, msgIndex) => {
      setBarErrorByKey((prev) => new Map(prev).set(key, ''))
      const t = resolveRatingTarget(
        msg,
        key,
        pickByKey,
        msgIndex,
        messagesRef.current
      )
      openDialog(
        key,
        msg.content,
        t.point_id || undefined,
        t.recipe_id || undefined,
        hint
      )
    },
    [pickByKey]
  )

  const handleThumbClick = useCallback(
    (key, msg, hint, msgIndex) => {
      const current = ratedThumbByKeyRef.current.get(key) ?? null
      if (current === hint) {
        setRatedThumbByKey((prev) => {
          const next = new Map(prev)
          next.delete(key)
          return next
        })
        onThumbRatingsChange?.(key, null)
        return
      }
      handleOpenRating(key, msg, hint, msgIndex)
    },
    [handleOpenRating, onThumbRatingsChange]
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
                      const { intro, recipe: parsedRecipe } = parseAssistantMessage(
                        msg.content
                      )
                      const rk = rateKey(msg, i)
                      const target = getRecipeTarget(msg, rk, pickByKey)
                      const { recipe: displayRecipe, showLibraryHint, cardTitle } =
                        buildDisplayRecipe(msg, rk, pickByKey, parsedRecipe)
                      const introRecipeName =
                        cardTitle || parsedRecipe?.recipe_name || ''
                      const hasRanked =
                        Array.isArray(msg.ranked_suggestions) &&
                        msg.ranked_suggestions.length > 0

                      if (displayRecipe) {
                        const anchorId = `assistant-recipe-${String(
                          msg.id ?? `idx-${i}`
                        ).replace(/[^a-zA-Z0-9_-]/g, '-')}`
                        const prompted =
                          sessionMeta?.rating_prompted &&
                          sessionMeta.rating_prompted[msg.id]
                        return (
                          <>
                            {prompted ? (
                              <p className="text-xs text-[#5C6E43]/90 mb-1">
                                Session suggested rating for this reply.
                              </p>
                            ) : null}
                            {hasRanked ? (
                              <>
                                {intro ? (
                                  <AssistantIntro
                                    intro={intro}
                                    recipeName={introRecipeName}
                                    anchorId={anchorId}
                                  />
                                ) : null}
                                <RecipeSuggestionsPicker
                                  suggestions={msg.ranked_suggestions}
                                  selectedPointId={target.point_id}
                                  disabled={isTyping}
                                  onSelect={(s) => handlePickSuggestion(rk, s, msg)}
                                />
                                <RecipeCard recipe={displayRecipe} anchorId={anchorId} />
                              </>
                            ) : (
                              <>
                                {intro ? (
                                  <AssistantIntro
                                    intro={intro}
                                    recipeName={introRecipeName}
                                    anchorId={anchorId}
                                  />
                                ) : null}
                                <RecipeCard recipe={displayRecipe} anchorId={anchorId} />
                              </>
                            )}
                          </>
                        )
                      }
                      return (
                        <PlainAssistantMarkdown text={msg.content} />
                      )
                    })()}
                    <BotRatingRow
                      disabled={isTyping}
                      thumbChosen={ratedThumbByKey.get(rateKey(msg, i)) ?? null}
                      barError={barErrorByKey.get(rateKey(msg, i)) ?? ''}
                      onThumbClick={(hint) =>
                        handleThumbClick(rateKey(msg, i), msg, hint, i)
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
