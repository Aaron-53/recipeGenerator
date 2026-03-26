import React, { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { IoFastFoodOutline } from 'react-icons/io5'
import { buildGenerateRecipePrompt } from '../utils/generateRecipePrompt'
import { getRecipeImageUrl } from '../utils/recipeImages'

const DESC_MAX = 160
const EAGER_FIRST = 6

function ListingCardImage({ src, safeTitle, listIndex }) {
  const [imgFailed, setImgFailed] = useState(false)
  const showImg = Boolean(src && !imgFailed)
  return showImg ? (
    <img
      src={src}
      alt={safeTitle}
      loading={listIndex < EAGER_FIRST ? 'eager' : 'lazy'}
      decoding="async"
      onError={() => setImgFailed(true)}
      className="h-full w-full object-cover transition-opacity duration-200 group-hover:brightness-40 group-focus-within:brightness-40"
    />
  ) : (
    <div
      className="flex h-full w-full items-center justify-center bg-gradient-to-br from-[#ead8b6] to-[#F6C7B7]/60 px-3 transition-opacity duration-200 group-hover:brightness-40 group-focus-within:brightness-40"
      role="img"
      aria-label="No recipe image"
    >
      <IoFastFoodOutline className="h-20 w-20 shrink-0 text-[#5C6E43]/45" aria-hidden />
    </div>
  )
}

function truncateDescription(text) {
  const t = String(text ?? '').trim()
  if (!t) return ''
  if (t.length <= DESC_MAX) return t
  return `${t.slice(0, DESC_MAX).trim()}…`
}

export default function RecipeListingCard({
  title,
  description,
  imageFilename,
  listIndex = 0,
}) {
  const safeTitle = title || 'Untitled recipe'

  const src = useMemo(() => {
    if (!imageFilename || String(imageFilename).trim() === '') return null
    return getRecipeImageUrl(imageFilename)
  }, [imageFilename])

  const imageKey = src || imageFilename || 'none'
  const generatePrompt = useMemo(
    () => buildGenerateRecipePrompt(safeTitle, description),
    [safeTitle, description]
  )

  return (
    <article className="group flex h-full flex-col overflow-hidden rounded-2xl border border-[#5C6E43]/25 bg-[#F6E7C8] shadow-lg transition-shadow hover:shadow-xl">
      <div className="relative mx-auto aspect-[420/277] w-full max-w-[420px] shrink-0 overflow-hidden p-2">
        <div className="relative h-full w-full overflow-hidden rounded-lg border-2 border-[#5C6E43]">
          <ListingCardImage
            key={imageKey}
            src={src}
            safeTitle={safeTitle}
            listIndex={listIndex}
          />
          <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center p-3 opacity-0 transition-opacity duration-200 group-hover:pointer-events-auto group-hover:opacity-100 group-focus-within:pointer-events-auto group-focus-within:opacity-100">
            <Link
              to="/generate-recipe"
              state={{ initialPrompt: generatePrompt }}
              className="pointer-events-auto rounded-lg border border-[#f5e8c7]/50 bg-[#5C6E43] px-3 py-1.5 text-center text-sm font-semibold text-[#f5e8c7] shadow-md transition-colors hover:bg-[#4a5a36] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f5e8c7]"
            >
              Generate recipe
            </Link>
          </div>
        </div>
      </div>
      <div className="flex min-h-0 flex-1 flex-col p-2 px-3 sm:px-4">
        <h3 className="line-clamp-2 text-base font-semibold leading-snug text-[#5C6E43] sm:text-lg">
          {safeTitle}
        </h3>
        <p className="mt-2 line-clamp-4 flex-1 text-sm leading-relaxed text-[#3d2b1f]/85">
          {truncateDescription(description)}
        </p>
      </div>
    </article>
  )
}
