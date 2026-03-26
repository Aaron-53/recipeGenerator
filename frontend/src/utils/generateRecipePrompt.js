export function buildGenerateRecipePrompt(title, descriptionRaw) {
  const t = String(title ?? 'Untitled recipe').replace(/\s+/g, ' ').trim()
  const d = String(descriptionRaw ?? '').replace(/\s+/g, ' ').trim()
  if (d) {
    return `Generate a recipe for "${t}". Here is how the catalog describes it: ${d}`
  }
  return `Generate a recipe for "${t}".`
}
