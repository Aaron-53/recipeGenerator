import React, { useState, useMemo, useRef, useCallback, useEffect } from 'react'
import Navbar from '../components/Navbar'
import ChatHistory from '../components/ChatHistory'
import ChatArea from '../components/ChatArea'

const HARDCODED_CHAT_TITLES = ['spicy vegan curry', 'spicy vegan curry', 'spicy vegan curry']

const BOT_REPLIES = [
  (q) =>
    `Love that energy! For "${snippet(q)}" I'd try a one-pan bake: olive oil, garlic, whatever herbs you have, 20 min at 200°C.`,
  (q) =>
    `Quick idea for "${snippet(q)}": chop everything bite-sized, high heat in the pan, finish with lemon or vinegar.`,
  (q) =>
    `Here's a tiny plan: starch + veg + protein in one bowl. Season bold, taste often. Want a sauce idea next?`,
  (q) =>
    `If you're short on time: canned beans + greens + canned tomatoes = soup in 15 minutes. Salt at the end.`,
  (q) =>
    `For "${snippet(q)}" I’d balance sweet/sour — a spoon of honey or sugar + something tangy works wonders.`,
  () =>
    `Pro tip: mise en place saves you when things move fast. Bowls for prepped items = fewer mistakes.`,
  (q) =>
    `Thinking about "${snippet(q)}": try the same dish twice this week — second time you'll nail timing.`,
  () =>
    `Leftovers? Fried rice, frittata, or wrap — three ways to reset the same ingredients.`,
  (q) =>
    `On "${snippet(q)}": don't crowd the pan; brown = flavor. Work in batches if needed.`,
  () =>
    `Herb rule: soft herbs (basil, parsley) at the end; hardy ones (rosemary, thyme) earlier.`,
  (q) =>
    `Nice one! "${snippet(q)}" could go Mediterranean: oregano, lemon zest, good olive oil.`,
  () =>
    `Temperature check: chicken to 74°C / 165°F, fish until opaque — trust a thermometer once in a while.`,
]

function snippet(text, max = 42) {
  const t = text.trim()
  if (t.length <= max) return t || 'that'
  return `${t.slice(0, max)}…`
}

function randomReply(userText) {
  const pick = BOT_REPLIES[Math.floor(Math.random() * BOT_REPLIES.length)]
  return typeof pick === 'function' ? pick(userText) : pick()
}

const Chat = () => {
  const [activeHistoryIndex, setActiveHistoryIndex] = useState(0)
  const [messages, setMessages] = useState([])
  const [isTyping, setIsTyping] = useState(false)
  const replyTimeoutRef = useRef(null)

  const titles = useMemo(() => HARDCODED_CHAT_TITLES, [])

  useEffect(() => {
    return () => {
      if (replyTimeoutRef.current) clearTimeout(replyTimeoutRef.current)
    }
  }, [])

  const handleSend = useCallback((text) => {
    const trimmed = text.trim()
    if (!trimmed) return

    if (replyTimeoutRef.current) {
      clearTimeout(replyTimeoutRef.current)
      replyTimeoutRef.current = null
    }

    const userId = crypto.randomUUID()
    setMessages((prev) => [...prev, { id: userId, role: 'user', content: trimmed }])
    setIsTyping(true)

    const delayMs = 450 + Math.random() * 1100
    replyTimeoutRef.current = setTimeout(() => {
      const botId = crypto.randomUUID()
      const reply = randomReply(trimmed)
      setMessages((prev) => [...prev, { id: botId, role: 'bot', content: reply }])
      setIsTyping(false)
      replyTimeoutRef.current = null
    }, delayMs)
  }, [])

  return (
    <div className="min-h-screen bg-[#5b6d44] flex flex-col">
      <Navbar />
      <main className="flex-1 px-10 pb-8 mx-auto w-full">
        <div className="flex flex-col gap-3 md:flex-row md:items-stretch">
          <ChatHistory
            titles={titles}
            activeIndex={activeHistoryIndex}
            onSelect={setActiveHistoryIndex}
          />
          <ChatArea messages={messages} onSend={handleSend} isTyping={isTyping} />
        </div>
      </main>
    </div>
  )
}

export default Chat
