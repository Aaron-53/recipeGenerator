function findRecipeJsonStart(t) {
  const anchored = /\{\s*"recipe_name"\s*:/.exec(t)
  if (anchored) return anchored.index
  return t.indexOf('{')
}

export function parseAssistantMessage(text) {
  if (text == null || typeof text !== 'string') {
    return { intro: '', recipe: null, raw: String(text) }
  }
  const t = text.trim()
  const start = findRecipeJsonStart(t)
  if (start === -1) {
    return { intro: t, recipe: null, raw: text }
  }

  let depth = 0
  for (let i = start; i < t.length; i++) {
    const c = t[i]
    if (c === '{') depth += 1
    else if (c === '}') {
      depth -= 1
      if (depth === 0) {
        const jsonStr = t.slice(start, i + 1)
        try {
          const obj = JSON.parse(jsonStr)
          if (
            obj &&
            typeof obj === 'object' &&
            typeof obj.recipe_name === 'string' &&
            Array.isArray(obj.ingredients)
          ) {
            return {
              intro: t.slice(0, start).trim(),
              recipe: obj,
              raw: text,
            }
          }
        } catch {
          break
        }
        break
      }
    }
  }

  return { intro: t, recipe: null, raw: text }
}

const MAX_SESSION_TITLE_LEN = 56

function truncateTitle(text) {
  const s = String(text ?? '').trim()
  if (!s) return 'New chat'
  if (s.length <= MAX_SESSION_TITLE_LEN) return s
  return `${s.slice(0, MAX_SESSION_TITLE_LEN - 3)}…`
}

export function deriveSessionTitle(messages) {
  if (!Array.isArray(messages) || messages.length === 0) {
    return 'New chat'
  }

  for (const m of messages) {
    if (m.role !== 'assistant' || !m.content) continue
    const { recipe } = parseAssistantMessage(m.content)
    const name = recipe?.recipe_name
    if (typeof name === 'string' && name.trim()) {
      return truncateTitle(name)
    }
  }

  const firstUser = messages.find((m) => m.role === 'user')
  if (firstUser?.content?.trim()) {
    return truncateTitle(firstUser.content)
  }

  return 'New chat'
}

function normalizeForRecipeMatch(s) {
  return String(s ?? '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .replace(/[""''`]/g, '')
    .replace(/[.!?]+$/g, '')
}

export function boldMatchesRecipeName(boldText, recipeName) {
  const a = normalizeForRecipeMatch(boldText)
  const b = normalizeForRecipeMatch(recipeName)
  if (!a || !b) return false
  if (a === b) return true
  if (Math.abs(a.length - b.length) > 24) return false
  return a.includes(b) || b.includes(a)
}

export function splitIntroMarkdown(intro) {
  if (!intro) return []
  const parts = []
  const re = /\*\*([\s\S]+?)\*\*/g
  let last = 0
  let m
  while ((m = re.exec(intro)) !== null) {
    if (m.index > last) {
      parts.push({ type: 'text', text: intro.slice(last, m.index) })
    }
    parts.push({ type: 'bold', text: m[1] })
    last = m.index + m[0].length
  }
  if (last < intro.length) {
    parts.push({ type: 'text', text: intro.slice(last) })
  }
  return parts.length ? parts : [{ type: 'text', text: intro }]
}

function splitTextByRecipeName(text, recipeName) {
  if (!text || !recipeName?.trim()) {
    return [{ type: 'text', text: text || '' }]
  }
  const escaped = recipeName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const re = new RegExp(`(${escaped})`, 'gi')
  const out = []
  let last = 0
  let m
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) {
      out.push({ type: 'text', text: text.slice(last, m.index) })
    }
    out.push({ type: 'recipeLink', text: m[1] })
    last = m.index + m[0].length
  }
  if (last < text.length) {
    out.push({ type: 'text', text: text.slice(last) })
  }
  return out.length ? out : [{ type: 'text', text }]
}

export function buildIntroSegments(intro, recipeName) {
  const md = splitIntroMarkdown(intro)
  const segments = []
  for (const p of md) {
    if (p.type === 'bold') {
      if (recipeName && boldMatchesRecipeName(p.text, recipeName)) {
        segments.push({ type: 'recipeLink', text: p.text.trim() })
      } else {
        segments.push({ type: 'bold', text: p.text })
      }
    } else {
      segments.push(...splitTextByRecipeName(p.text, recipeName))
    }
  }
  return segments
}
