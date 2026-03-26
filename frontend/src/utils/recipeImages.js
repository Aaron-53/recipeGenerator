function publicAssetRoot() {
  const b = import.meta.env.BASE_URL || '/'
  return b.endsWith('/') ? b : `${b}/`
}

const HAS_IMAGE_EXT = /\.(jpe?g|png|gif|webp)$/i
const SAFE_FILENAME = /^[a-zA-Z0-9._-]+$/

export function resolveRecipeImageFileName(filename) {
  if (filename == null || String(filename).trim() === '') return null
  let name = String(filename).trim()
  if (!HAS_IMAGE_EXT.test(name)) name = `${name}.jpg`
  return name
}

export function getRecipeImageUrl(filename) {
  const name = resolveRecipeImageFileName(filename)
  if (!name) return null
  const segment = SAFE_FILENAME.test(name) ? name : encodeURIComponent(name)
  return `${publicAssetRoot()}recipe-images/${segment}`
}
